from datetime import UTC, datetime

from promptguard.repositories.database import FindingRecord, TestResultRecord

REMEDIATION = {
    "LLM01": "Strengthen instruction hierarchy, isolate untrusted context, and test multi-turn boundaries.",
    "LLM02": "Remove secrets from model context and add canary-based disclosure tests.",
    "LLM05": "Escape and validate model output before downstream rendering or execution.",
    "LLM06": "Require explicit approval and scope checks before tool invocation.",
    "LLM07": "Keep system prompts out of retrievable context and block direct disclosure.",
}


def finding_from_result(result: TestResultRecord, target_id: str) -> FindingRecord | None:
    if result.outcome not in {"failed", "manual_review"}:
        return None
    now = datetime.now(UTC)
    return FindingRecord(
        title=f"{result.owasp_category} {result.test_id} requires attention",
        owasp_category=result.owasp_category,
        severity=result.severity,
        status="open",
        description=result.evaluator_reasoning,
        evidence=result.redacted_response[:1000],
        remediation=REMEDIATION.get(
            result.owasp_category,
            "Review the result evidence and apply controls appropriate to the application context.",
        ),
        affected_target=target_id,
        related_result_ids_json=f"[{result.id}]",
        first_observed=now,
        last_observed=now,
    )
