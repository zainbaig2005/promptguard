from pathlib import Path

import pytest

from promptguard.exceptions import ValidationError
from promptguard.target_loader import load_configured_targets, target_by_id


def test_load_openai_compatible_target_config(tmp_path: Path) -> None:
    config = tmp_path / "targets.yaml"
    config.write_text(
        """
        targets:
          - id: authorized-api
            name: Authorized API
            adapter_type: openai-compatible
            base_url: https://api.example.test/v1
            model_name: demo-model
            authentication_ref: AUTHORIZED_LLM_API_KEY
            request_config:
              temperature: 0
              max_tokens: 128
        """,
        encoding="utf-8",
    )

    targets = load_configured_targets(config)

    assert targets[0].id == "authorized-api"
    assert targets[0].authentication_ref == "AUTHORIZED_LLM_API_KEY"


def test_target_by_id_includes_configured_targets(tmp_path: Path) -> None:
    config = tmp_path / "targets.yaml"
    config.write_text(
        """
        targets:
          - id: custom-target
            name: Custom Target
            adapter_type: generic-rest
            base_url: https://api.example.test/invoke
        """,
        encoding="utf-8",
    )

    assert target_by_id("custom-target", config).adapter_type == "generic-rest"


def test_invalid_targets_shape_fails(tmp_path: Path) -> None:
    config = tmp_path / "targets.yaml"
    config.write_text("targets: nope\n", encoding="utf-8")

    with pytest.raises(ValidationError):
        load_configured_targets(config)
