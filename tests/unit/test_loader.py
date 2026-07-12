from pathlib import Path

from promptguard.test_loader import load_suite


def test_starter_suite_has_sixty_tests() -> None:
    suite = load_suite(Path("data/test_suites/owasp_2025_starter.yaml"))
    assert len(suite.tests) >= 60
    assert {test.owasp_category.value for test in suite.tests} == {f"LLM{i:02d}" for i in range(1, 11)}


def test_gemini_smoke_suite_is_small() -> None:
    suite = load_suite(Path("data/test_suites/gemini_smoke.yaml"))
    assert suite.id == "gemini-smoke"
    assert len(suite.tests) == 6
