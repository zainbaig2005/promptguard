from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import Boolean, DateTime, Engine, Float, ForeignKey, Integer, String, Text, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker


class Base(DeclarativeBase):
    pass


class TargetRecord(Base):
    __tablename__ = "targets"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    adapter_type: Mapped[str] = mapped_column(String, nullable=False)
    base_url: Mapped[str | None] = mapped_column(String)
    model_name: Mapped[str | None] = mapped_column(String)
    request_config_json: Mapped[str] = mapped_column(Text, default="{}")
    authentication_ref: Mapped[str | None] = mapped_column(String)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class TestRunRecord(Base):
    __tablename__ = "test_runs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    suite_id: Mapped[str] = mapped_column(String, index=True)
    target_id: Mapped[str] = mapped_column(ForeignKey("targets.id"), index=True)
    status: Mapped[str] = mapped_column(String, index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_tests: Mapped[int] = mapped_column(Integer, default=0)
    configuration_snapshot_json: Mapped[str] = mapped_column(Text, default="{}")
    authorization_confirmation: Mapped[bool] = mapped_column(Boolean, default=False)
    framework_version: Mapped[str] = mapped_column(String, default="0.1.0")
    environment_metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    notes: Mapped[str | None] = mapped_column(Text)
    target: Mapped[TargetRecord] = relationship()
    results: Mapped[list[TestResultRecord]] = relationship(back_populates="run", cascade="all, delete-orphan")


class TestResultRecord(Base):
    __tablename__ = "test_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("test_runs.id"), index=True)
    test_id: Mapped[str] = mapped_column(String, index=True)
    owasp_category: Mapped[str] = mapped_column(String, index=True)
    outcome: Mapped[str] = mapped_column(String, index=True)
    severity: Mapped[str] = mapped_column(String, index=True)
    prompt: Mapped[str] = mapped_column(Text)
    redacted_prompt: Mapped[str] = mapped_column(Text)
    response: Mapped[str] = mapped_column(Text)
    redacted_response: Mapped[str] = mapped_column(Text)
    expected_behavior: Mapped[str] = mapped_column(Text)
    evaluator_reasoning: Mapped[str] = mapped_column(Text)
    evaluator_name: Mapped[str] = mapped_column(String)
    evaluator_version: Mapped[str] = mapped_column(String)
    confidence: Mapped[float] = mapped_column(Float)
    latency_ms: Mapped[float] = mapped_column(Float)
    request_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    response_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    response_length: Mapped[int] = mapped_column(Integer)
    approximate_input_tokens: Mapped[int] = mapped_column(Integer)
    approximate_output_tokens: Mapped[int] = mapped_column(Integer)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)
    error_message: Mapped[str | None] = mapped_column(Text)
    evidence_path: Mapped[str | None] = mapped_column(String)
    tags_json: Mapped[str] = mapped_column(Text, default="[]")
    raw_metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    run: Mapped[TestRunRecord] = relationship(back_populates="results")


class FindingRecord(Base):
    __tablename__ = "findings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String)
    owasp_category: Mapped[str] = mapped_column(String, index=True)
    severity: Mapped[str] = mapped_column(String, index=True)
    status: Mapped[str] = mapped_column(String, default="open", index=True)
    description: Mapped[str] = mapped_column(Text)
    evidence: Mapped[str] = mapped_column(Text)
    remediation: Mapped[str] = mapped_column(Text)
    affected_target: Mapped[str] = mapped_column(String)
    related_result_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    first_observed: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_observed: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    false_positive: Mapped[bool] = mapped_column(Boolean, default=False)
    analyst_notes: Mapped[str] = mapped_column(Text, default="")


def engine_from_url(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, connect_args=connect_args, future=True)
    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection: Any, _connection_record: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def init_database(database_url: str) -> sessionmaker[Session]:
    if database_url.startswith("sqlite:///"):
        db_path = Path(database_url.replace("sqlite:///", "", 1))
        if db_path.parent != Path("."):
            db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = engine_from_url(database_url)
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)


def dumps(value: Any) -> str:
    return json.dumps(value, default=str, sort_keys=True)


def loads(value: str) -> Any:
    return json.loads(value) if value else None
