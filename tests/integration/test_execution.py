import pytest

from promptguard.demo import target_by_id
from promptguard.execution.engine import ExecutionEngine
from promptguard.repositories.database import init_database
from promptguard.test_loader import load_suite


@pytest.mark.asyncio
async def test_full_run_against_mock(tmp_path) -> None:
    suite = load_suite(__import__("pathlib").Path("data/test_suites/owasp_2025_starter.yaml"))
    session_factory = init_database(f"sqlite:///{tmp_path}/test.db")
    summary = await ExecutionEngine(session_factory, max_concurrency=4).run_suite(
        suite, target_by_id("local-mock-mixed"), authorization_confirmed=True
    )
    assert summary.total_tests == len(suite.tests)
    assert summary.failed > 0
    assert summary.manual_review > 0
