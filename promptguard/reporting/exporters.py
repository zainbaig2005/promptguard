import csv
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session

from promptguard.repositories.database import TestResultRecord, TestRunRecord, loads
from promptguard.services.metrics import summarize_results


def export_json(session: Session, run_id: str, output: Path) -> Path:
    run = session.get(TestRunRecord, run_id)
    if run is None:
        raise ValueError(f"Unknown run id: {run_id}")
    data = {
        "run": {"id": run.id, "suite_id": run.suite_id, "target_id": run.target_id, "status": run.status},
        "results": [row_to_dict(item) for item in run.results],
        "metrics": summarize_results(run.results),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    return output


def export_csv(session: Session, run_id: str, output: Path) -> Path:
    run = session.get(TestRunRecord, run_id)
    if run is None:
        raise ValueError(f"Unknown run id: {run_id}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["test_id", "owasp_category", "outcome", "severity", "confidence", "latency_ms"]
        )
        writer.writeheader()
        for item in run.results:
            writer.writerow({key: getattr(item, key) for key in writer.fieldnames})
    return output


def export_html(session: Session, run_id: str, output: Path) -> Path:
    run = session.get(TestRunRecord, run_id)
    if run is None:
        raise ValueError(f"Unknown run id: {run_id}")
    env = Environment(loader=FileSystemLoader("promptguard/reporting/templates"), autoescape=select_autoescape())
    html = env.get_template("report.html.j2").render(run=run, metrics=summarize_results(run.results), loads=loads)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    return output


def row_to_dict(item: TestResultRecord) -> dict[str, object]:
    return {
        "test_id": item.test_id,
        "owasp_category": item.owasp_category,
        "outcome": item.outcome,
        "severity": item.severity,
        "prompt": item.redacted_prompt,
        "response": item.redacted_response,
        "reasoning": item.evaluator_reasoning,
        "confidence": item.confidence,
        "latency_ms": item.latency_ms,
    }
