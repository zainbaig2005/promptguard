from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from promptguard.models.enums import AssessmentMode, OwaspCategory, ResultOutcome, RunStatus, Severity


def now_utc() -> datetime:
    return datetime.now(UTC)


class ExpectedBehavior(BaseModel):
    type: str
    values: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)


class EvaluatorConfig(BaseModel):
    type: str
    config: dict[str, Any] = Field(default_factory=dict)


class TestCase(BaseModel):
    __test__: ClassVar[bool] = False
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    description: str
    owasp_category: OwaspCategory
    assessment_mode: AssessmentMode
    test_type: str
    prompt: str
    expected_behavior: ExpectedBehavior
    evaluator: EvaluatorConfig
    severity: Severity
    tags: list[str] = Field(default_factory=list)
    requires_authorization: bool = True
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    max_response_characters: int = Field(default=10000, ge=1, le=100000)
    setup_data: dict[str, Any] | None = None
    cleanup: str | None = None
    source_classification: str = "original"

    @field_validator("id")
    @classmethod
    def id_must_be_stable(cls, value: str) -> str:
        if not value or " " in value:
            raise ValueError("test id must be non-empty and contain no spaces")
        return value


class TestSuite(BaseModel):
    id: str
    name: str
    description: str
    version: str
    tests: list[TestCase]

    @property
    def selected_test_ids(self) -> list[str]:
        return [test.id for test in self.tests]


class Target(BaseModel):
    id: str
    name: str
    description: str = ""
    adapter_type: str = "mock"
    base_url: str | None = None
    model_name: str | None = None
    health_check_path: str | None = None
    request_config: dict[str, Any] = Field(default_factory=dict)
    authentication_ref: str | None = None
    enabled: bool = True
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class AdapterResponse(BaseModel):
    text: str
    latency_ms: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluationResult(BaseModel):
    outcome: ResultOutcome
    confidence: float = Field(ge=0, le=1)
    reasoning: str
    evaluator_name: str
    evaluator_version: str = "0.1.0"
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunSummary(BaseModel):
    run_id: str
    status: RunStatus
    total_tests: int
    passed: int
    failed: int
    manual_review: int
    errors: int
