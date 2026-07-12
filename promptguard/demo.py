import asyncio
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from promptguard.config import get_settings
from promptguard.execution.engine import ExecutionEngine
from promptguard.models.schemas import Target
from promptguard.repositories.database import TargetRecord, init_database
from promptguard.test_loader import load_suite


def demo_targets() -> list[Target]:
    return [
        Target(
            id="local-mock-secure", name="Local Mock Secure", adapter_type="mock", request_config={"profile": "secure"}
        ),
        Target(
            id="local-mock-vulnerable",
            name="Local Mock Vulnerable",
            adapter_type="mock",
            request_config={"profile": "vulnerable"},
        ),
        Target(
            id="local-mock-mixed", name="Local Mock Mixed", adapter_type="mock", request_config={"profile": "mixed"}
        ),
    ]


def seed_targets(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        for target in demo_targets():
            if session.get(TargetRecord, target.id) is None:
                session.add(
                    TargetRecord(
                        id=target.id,
                        name=target.name,
                        description=target.description,
                        adapter_type=target.adapter_type,
                        request_config_json=target.model_dump_json(),
                    )
                )
        session.commit()


async def seed_demo_runs() -> list[str]:
    settings = get_settings()
    session_factory = init_database(settings.database_url)
    seed_targets(session_factory)
    suite = load_suite(Path("data/test_suites/owasp_2025_starter.yaml"))
    engine = ExecutionEngine(session_factory, max_concurrency=settings.max_concurrency)
    run_ids = []
    for target in demo_targets():
        summary = await engine.run_suite(suite, target, authorization_confirmed=True)
        run_ids.append(summary.run_id)
    return run_ids


def target_by_id(target_id: str) -> Target:
    for target in demo_targets():
        if target.id == target_id:
            return target
    raise ValueError(f"Unknown demo target: {target_id}")


def list_target_ids(session_factory: sessionmaker[Session]) -> list[str]:
    with session_factory() as session:
        rows = session.scalars(select(TargetRecord.id).order_by(TargetRecord.id)).all()
        return list(rows) or [target.id for target in demo_targets()]


def seed_demo_sync() -> list[str]:
    return asyncio.run(seed_demo_runs())
