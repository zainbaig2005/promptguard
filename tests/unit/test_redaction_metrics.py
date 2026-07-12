from promptguard.security.redaction import RedactionService
from promptguard.services.metrics import estimate_cost, estimate_tokens


def test_redaction_removes_promptguard_canary() -> None:
    assert "PROMPTGUARD" not in RedactionService().redact("x PROMPTGUARD_TEST_SECRET_7F3A91")


def test_cost_estimate_is_non_negative() -> None:
    assert estimate_tokens("hello world") > 0
    assert estimate_cost(10, 20) >= 0
