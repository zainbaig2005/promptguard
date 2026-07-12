from enum import StrEnum


class OwaspCategory(StrEnum):
    LLM01 = "LLM01"
    LLM02 = "LLM02"
    LLM03 = "LLM03"
    LLM04 = "LLM04"
    LLM05 = "LLM05"
    LLM06 = "LLM06"
    LLM07 = "LLM07"
    LLM08 = "LLM08"
    LLM09 = "LLM09"
    LLM10 = "LLM10"


OWASP_LABELS = {
    OwaspCategory.LLM01: "Prompt Injection",
    OwaspCategory.LLM02: "Sensitive Information Disclosure",
    OwaspCategory.LLM03: "Supply Chain",
    OwaspCategory.LLM04: "Data and Model Poisoning",
    OwaspCategory.LLM05: "Improper Output Handling",
    OwaspCategory.LLM06: "Excessive Agency",
    OwaspCategory.LLM07: "System Prompt Leakage",
    OwaspCategory.LLM08: "Vector and Embedding Weaknesses",
    OwaspCategory.LLM09: "Misinformation",
    OwaspCategory.LLM10: "Unbounded Consumption",
}


class AssessmentMode(StrEnum):
    AUTOMATED = "automated"
    ASSISTED = "assisted"
    MANUAL = "manual"
    ARCHITECTURE_REVIEW = "architecture_review"


class Severity(StrEnum):
    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ResultOutcome(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    MANUAL_REVIEW = "manual_review"
    ERROR = "error"
    SKIPPED = "skipped"
    NOT_APPLICABLE = "not_applicable"


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    CANCELLED = "cancelled"
    FAILED = "failed"


class FindingStatus(StrEnum):
    OPEN = "open"
    MITIGATED = "mitigated"
    ACCEPTED_RISK = "accepted_risk"
