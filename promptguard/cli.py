from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy.orm import Session, sessionmaker

from promptguard.config import get_settings
from promptguard.demo import seed_demo_runs, seed_targets
from promptguard.execution.engine import ExecutionEngine
from promptguard.reporting.exporters import export_csv, export_html, export_json
from promptguard.repositories.database import TestRunRecord, init_database
from promptguard.target_loader import all_targets, target_by_id
from promptguard.test_loader import load_suite, load_suites

app = typer.Typer(help="PromptGuard authorized LLM security validation framework.")
console = Console()
SuiteDirArg = Annotated[Path, typer.Argument()]
StarterSuiteArg = Annotated[Path, typer.Argument()]


def session_factory() -> sessionmaker[Session]:
    return init_database(get_settings().database_url)


@app.command()
def init() -> None:
    init_database(get_settings().database_url)
    console.print("[green]Database initialized.[/green]")


@app.command("seed-demo")
def seed_demo() -> None:
    runs = asyncio.run(seed_demo_runs())
    console.print(f"[green]Seeded demo runs:[/green] {', '.join(runs)}")


@app.command("validate-tests")
def validate_tests(path: SuiteDirArg = Path("data/test_suites")) -> None:
    suites = load_suites(path)
    console.print(
        f"[green]Validated {sum(len(suite.tests) for suite in suites)} tests across {len(suites)} suite(s).[/green]"
    )


@app.command("list-tests")
def list_tests(path: StarterSuiteArg = Path("data/test_suites/owasp_2025_starter.yaml")) -> None:
    suite = load_suite(path)
    table = Table("ID", "Category", "Mode", "Severity", "Name")
    for test in suite.tests:
        table.add_row(test.id, test.owasp_category.value, test.assessment_mode.value, test.severity.value, test.name)
    console.print(table)


@app.command("list-suites")
def list_suites(path: SuiteDirArg = Path("data/test_suites")) -> None:
    for suite in load_suites(path):
        console.print(f"{suite.id}: {suite.name} ({len(suite.tests)} tests)")


@app.command("list-targets")
def list_targets() -> None:
    sf = session_factory()
    seed_targets(sf)
    table = Table("ID", "Name", "Adapter", "Auth Env")
    for target in all_targets():
        table.add_row(target.id, target.name, target.adapter_type, target.authentication_ref or "")
    console.print(table)


@app.command("dry-run")
def dry_run(suite: str = "owasp-2025-starter", target: str = "local-mock-mixed") -> None:
    test_suite = load_suite(Path("data/test_suites/owasp_2025_starter.yaml"))
    summary = asyncio.run(
        ExecutionEngine(session_factory()).run_suite(
            test_suite, target_by_id(target), authorization_confirmed=True, dry_run=True
        )
    )
    console.print(f"Dry run {suite} against {target}: {summary.total_tests} tests would execute.")


@app.command()
def run(
    suite: str = "owasp-2025-starter",
    target: str = "local-mock-mixed",
    yes: bool = typer.Option(False, "--yes", help="Confirm authorization."),
) -> None:
    if not yes:
        raise typer.BadParameter("Pass --yes to confirm you are authorized to test this target.")
    test_suite = load_suite(Path("data/test_suites/owasp_2025_starter.yaml"))
    summary = asyncio.run(
        ExecutionEngine(session_factory()).run_suite(test_suite, target_by_id(target), authorization_confirmed=True)
    )
    console.print(
        f"[green]{summary.run_id}[/green] completed: {summary.passed} passed, "
        f"{summary.failed} failed, {summary.manual_review} manual review, {summary.errors} errors."
    )


@app.command("show-run")
def show_run(run_id: str) -> None:
    with session_factory()() as session:
        run_record = session.get(TestRunRecord, run_id)
        if run_record is None:
            raise typer.BadParameter(f"Unknown run id: {run_id}")
        table = Table("Test", "Category", "Outcome", "Severity")
        for result in run_record.results:
            table.add_row(result.test_id, result.owasp_category, result.outcome, result.severity)
        console.print(table)


@app.command()
def export(run_id: str, format: str = "html", output: Path | None = None) -> None:
    output = output or Path("reports") / f"{run_id}.{format}"
    with session_factory()() as session:
        if format == "html":
            path = export_html(session, run_id, output)
        elif format == "json":
            path = export_json(session, run_id, output)
        elif format == "csv":
            path = export_csv(session, run_id, output)
        else:
            raise typer.BadParameter("format must be html, json, or csv")
    console.print(f"[green]Exported[/green] {path}")


@app.command()
def serve() -> None:
    console.print("Run: streamlit run promptguard/dashboard/app.py")


if __name__ == "__main__":
    app()
