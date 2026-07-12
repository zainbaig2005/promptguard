from promptguard.evaluators.factory import evaluate_response
from promptguard.models.enums import AssessmentMode, OwaspCategory, Severity
from promptguard.models.schemas import AdapterResponse, EvaluatorConfig, ExpectedBehavior, TestCase


def make_case(evaluator: str = "must_not_contain") -> TestCase:
    return TestCase(
        id="LLM01-TEST-001",
        name="test",
        description="test",
        owasp_category=OwaspCategory.LLM01,
        assessment_mode=AssessmentMode.AUTOMATED,
        test_type="single_turn",
        prompt="prompt",
        expected_behavior=ExpectedBehavior(type=evaluator, values=["SECRET"]),
        evaluator=EvaluatorConfig(type=evaluator),
        severity=Severity.HIGH,
    )


def test_must_not_contain_fails_on_canary() -> None:
    result = evaluate_response(make_case(), AdapterResponse(text="SECRET", latency_ms=1))
    assert result.outcome == "failed"


def test_must_not_contain_passes_without_canary() -> None:
    result = evaluate_response(make_case(), AdapterResponse(text="clean", latency_ms=1))
    assert result.outcome == "passed"
