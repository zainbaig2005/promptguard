from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from pydantic import ValidationError as PydanticValidationError

from promptguard.exceptions import ValidationError
from promptguard.models.schemas import TestSuite

TEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["id", "name", "description", "version", "tests"],
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "description": {"type": "string"},
        "version": {"type": "string"},
        "tests": {"type": "array", "minItems": 1, "items": {"type": "object"}},
    },
    "additionalProperties": False,
}


def load_suite(path: Path) -> TestSuite:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValidationError(f"Invalid YAML in {path}: {exc}") from exc
    errors = sorted(Draft202012Validator(TEST_SCHEMA).iter_errors(data), key=lambda item: list(item.path))
    if errors:
        message = "; ".join(f"{'/'.join(map(str, error.path))}: {error.message}" for error in errors)
        raise ValidationError(f"Suite schema validation failed for {path}: {message}")
    try:
        return TestSuite.model_validate(data)
    except PydanticValidationError as exc:
        raise ValidationError(str(exc)) from exc


def load_suites(path: Path) -> list[TestSuite]:
    files = sorted(path.glob("*.yaml")) if path.is_dir() else [path]
    return [load_suite(file) for file in files]
