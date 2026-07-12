from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError as PydanticValidationError

from promptguard.demo import demo_targets
from promptguard.exceptions import ValidationError
from promptguard.models.schemas import Target

DEFAULT_TARGET_CONFIG = Path("config/targets.yaml")


def load_configured_targets(path: Path = DEFAULT_TARGET_CONFIG) -> list[Target]:
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ValidationError(f"Invalid target YAML in {path}: {exc}") from exc

    raw_targets: Any = data.get("targets", [])
    if not isinstance(raw_targets, list):
        raise ValidationError(f"{path} must contain a top-level 'targets' list.")

    targets: list[Target] = []
    for index, raw_target in enumerate(raw_targets, start=1):
        try:
            targets.append(Target.model_validate(raw_target))
        except PydanticValidationError as exc:
            raise ValidationError(f"Invalid target #{index} in {path}: {exc}") from exc
    return targets


def all_targets(path: Path = DEFAULT_TARGET_CONFIG) -> list[Target]:
    configured_by_id = {target.id: target for target in load_configured_targets(path)}
    demo_by_id = {target.id: target for target in demo_targets()}
    return [*demo_by_id.values(), *configured_by_id.values()]


def target_by_id(target_id: str, path: Path = DEFAULT_TARGET_CONFIG) -> Target:
    for target in all_targets(path):
        if target.id == target_id:
            return target
    raise ValidationError(f"Unknown target '{target_id}'. Run 'promptguard list-targets' to see available targets.")
