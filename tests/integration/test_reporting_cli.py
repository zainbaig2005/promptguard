from typer.testing import CliRunner

from promptguard.cli import app


def test_cli_validate_tests() -> None:
    result = CliRunner().invoke(app, ["validate-tests", "data/test_suites"])
    assert result.exit_code == 0
    assert "Validated" in result.output
