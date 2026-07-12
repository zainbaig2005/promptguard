from __future__ import annotations

import asyncio
import platform
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker

from promptguard.adapters.factory import create_adapter
from promptguard.constants import FRAMEWORK_VERSION, SYSTEM_CANARY, TEST_SECRET
from promptguard.evaluators.factory import evaluate_response
from promptguard.models.enums import AssessmentMode, ResultOutcome, RunStatus
from promptguard.models.schemas import AdapterResponse, RunSummary, Target, TestCase, TestSuite
from promptguard.repositories.database import TargetRecord, TestResultRecord, TestRunRecord, dumps
from promptguard.security.redaction import RedactionService
from promptguard.services.findings import finding_from_result
from promptguard.services.metrics import estimate_cost, estimate_tokens


class ExecutionEngine:
    def __init__(self, session_factory: sessionmaker[Session], max_concurrency: int = 3) -> None:
        self.session_factory = session_factory
        self.max_concurrency = max(1, max_concurrency)

    async def run_suite(
        self,
        suite: TestSuite,
        target: Target,
        authorization_confirmed: bool,
        dry_run: bool = False,
        category_filter: set[str] | None = None,
    ) -> RunSummary:
        if not authorization_confirmed:
            raise PermissionError("Authorization confirmation is required before executing tests.")
        selected = [test for test in suite.tests if not category_filter or test.owasp_category.value in category_filter]
        run_id = f"RUN-{uuid.uuid4().hex[:12].upper()}"
        if dry_run:
            return RunSummary(
                run_id=run_id,
                status=RunStatus.QUEUED,
                total_tests=len(selected),
                passed=0,
                failed=0,
                manual_review=0,
                errors=0,
            )

        redactor = RedactionService([SYSTEM_CANARY, TEST_SECRET])
        adapter = create_adapter(target)
        await adapter.validate_configuration()
        with self.session_factory() as session:
            self._upsert_target(session, target)
            run = TestRunRecord(
                id=run_id,
                suite_id=suite.id,
                target_id=target.id,
                status=RunStatus.RUNNING.value,
                start_time=datetime.now(UTC),
                end_time=None,
                total_tests=len(selected),
                configuration_snapshot_json=suite.model_dump_json(),
                authorization_confirmation=True,
                framework_version=FRAMEWORK_VERSION,
                environment_metadata_json=dumps({"python": platform.python_version(), "platform": platform.platform()}),
            )
            session.add(run)
            session.commit()

        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def execute_one(test_case: TestCase) -> None:
            async with semaphore:
                request_time = datetime.now(UTC)
                try:
                    if test_case.assessment_mode in {AssessmentMode.MANUAL, AssessmentMode.ARCHITECTURE_REVIEW}:
                        adapter_response = AdapterResponse(
                            text="Manual or architecture review item recorded for analyst assessment.", latency_ms=0
                        )
                    else:
                        adapter_response = await asyncio.wait_for(
                            adapter.send_message(test_case.prompt, test_case), timeout=test_case.timeout_seconds
                        )
                    evaluation = evaluate_response(test_case, adapter_response)
                    error = None
                except Exception as exc:
                    adapter_response = AdapterResponse(text="", latency_ms=0, metadata={})
                    evaluation = evaluate_response(test_case, adapter_response)
                    evaluation.outcome = ResultOutcome.ERROR
                    evaluation.reasoning = "Execution error; see error message."
                    error = str(exc)
                response_time = datetime.now(UTC)
                input_tokens = estimate_tokens(test_case.prompt)
                output_tokens = estimate_tokens(adapter_response.text)
                record = TestResultRecord(
                    run_id=run_id,
                    test_id=test_case.id,
                    owasp_category=test_case.owasp_category.value,
                    outcome=evaluation.outcome.value,
                    severity=test_case.severity.value,
                    prompt=test_case.prompt,
                    redacted_prompt=redactor.redact(test_case.prompt),
                    response=adapter_response.text,
                    redacted_response=redactor.redact(adapter_response.text),
                    expected_behavior=test_case.expected_behavior.model_dump_json(),
                    evaluator_reasoning=evaluation.reasoning,
                    evaluator_name=evaluation.evaluator_name,
                    evaluator_version=evaluation.evaluator_version,
                    confidence=evaluation.confidence,
                    latency_ms=adapter_response.latency_ms,
                    request_timestamp=request_time,
                    response_timestamp=response_time,
                    response_length=len(adapter_response.text),
                    approximate_input_tokens=input_tokens,
                    approximate_output_tokens=output_tokens,
                    estimated_cost=estimate_cost(input_tokens, output_tokens),
                    error_message=error,
                    evidence_path=None,
                    tags_json=dumps(test_case.tags),
                    raw_metadata_json=dumps({**adapter_response.metadata, **evaluation.metadata}),
                )
                with self.session_factory() as session:
                    session.add(record)
                    session.flush()
                    finding = finding_from_result(record, target.id)
                    if finding:
                        session.add(finding)
                    session.commit()

        await asyncio.gather(*(execute_one(test) for test in selected))
        await adapter.close()
        with self.session_factory() as session:
            completed_run = session.get(TestRunRecord, run_id)
            assert completed_run is not None
            counts = {outcome: 0 for outcome in ResultOutcome}
            for result_record in completed_run.results:
                counts[ResultOutcome(result_record.outcome)] += 1
            completed_run.status = (
                RunStatus.COMPLETED_WITH_ERRORS.value if counts[ResultOutcome.ERROR] else RunStatus.COMPLETED.value
            )
            completed_run.end_time = datetime.now(UTC)
            session.commit()
            return RunSummary(
                run_id=run_id,
                status=RunStatus(completed_run.status),
                total_tests=len(selected),
                passed=counts[ResultOutcome.PASSED],
                failed=counts[ResultOutcome.FAILED],
                manual_review=counts[ResultOutcome.MANUAL_REVIEW],
                errors=counts[ResultOutcome.ERROR],
            )

    def _upsert_target(self, session: Session, target: Target) -> None:
        record = session.get(TargetRecord, target.id)
        if record is None:
            record = TargetRecord(id=target.id, name=target.name, adapter_type=target.adapter_type)
            session.add(record)
        record.name = target.name
        record.description = target.description
        record.adapter_type = target.adapter_type
        record.base_url = target.base_url
        record.model_name = target.model_name
        record.request_config_json = dumps(target.request_config)
        record.authentication_ref = target.authentication_ref
        record.enabled = target.enabled
        session.commit()
