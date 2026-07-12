import re

SECRET_PATTERNS = [
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]+", re.I),
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"PROMPTGUARD_[A-Z0-9_]+"),
]


class RedactionService:
    def __init__(self, sensitive_values: list[str] | None = None) -> None:
        self.sensitive_values = [value for value in sensitive_values or [] if value]

    def redact(self, text: str) -> str:
        redacted = text
        for value in self.sensitive_values:
            redacted = redacted.replace(value, "[REDACTED]")
        for pattern in SECRET_PATTERNS:
            redacted = pattern.sub("[REDACTED]", redacted)
        return redacted
