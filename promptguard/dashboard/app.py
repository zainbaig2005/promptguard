from __future__ import annotations

import asyncio
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import select

from promptguard.config import get_settings
from promptguard.demo import seed_demo_sync
from promptguard.execution.engine import ExecutionEngine
from promptguard.models.schemas import TestSuite
from promptguard.repositories.database import FindingRecord, TestResultRecord, TestRunRecord, init_database
from promptguard.services.metrics import compare_runs, summarize_results
from promptguard.target_loader import all_targets, target_by_id
from promptguard.test_loader import load_suite, load_suites

st.set_page_config(page_title="PromptGuard", page_icon="PG", layout="wide")
st.markdown(
    "<style>"
    ".pg-wordmark{font-size:1.7rem;font-weight:800;color:#102a43}"
    ".badge{padding:.15rem .45rem;border-radius:.35rem;background:#e6f6ff}"
    "</style>",
    unsafe_allow_html=True,
)
st.markdown('<div class="pg-wordmark">PromptGuard</div>', unsafe_allow_html=True)

settings = get_settings()
SessionFactory = init_database(settings.database_url)


def query_all(model):
    with SessionFactory() as session:
        return list(session.scalars(select(model)).all())


def available_suites() -> list[TestSuite]:
    return load_suites(Path("data/test_suites"))


page = st.sidebar.radio(
    "Navigation",
    [
        "Overview",
        "Run Tests",
        "Runs",
        "Run Details",
        "Findings",
        "Test Library",
        "Targets",
        "Architecture Review",
        "Settings",
    ],
)

if page == "Overview":
    st.header("Security Validation Overview")
    runs = query_all(TestRunRecord)
    results = query_all(TestResultRecord)
    findings = query_all(FindingRecord)
    metrics = summarize_results(results)
    cols = st.columns(6)
    labels = ["total", "pass_rate", "failed", "manual_review", "errors", "estimated_cost"]
    for col, label in zip(cols, labels, strict=False):
        col.metric(label.replace("_", " ").title(), metrics[label])
    if results:
        df = pd.DataFrame(
            [
                {
                    "category": r.owasp_category,
                    "outcome": r.outcome,
                    "severity": r.severity,
                    "latency": r.latency_ms,
                    "test": r.test_id,
                }
                for r in results
            ]
        )
        left, right = st.columns(2)
        left.plotly_chart(
            px.histogram(df, x="category", color="outcome", title="Outcomes by Category"), use_container_width=True
        )
        right.plotly_chart(px.histogram(df, x="severity", title="Findings by Severity"), use_container_width=True)
        st.plotly_chart(px.box(df, x="category", y="latency", title="Latency Distribution"), use_container_width=True)
    else:
        st.info("No results yet. Use Seed Demo or run the starter suite against a local mock target.")
    if st.button("Seed Demo Data"):
        seed_demo_sync()
        st.rerun()

elif page == "Run Tests":
    st.header("Run Tests")
    suites = available_suites()
    suite_by_id = {suite.id: suite for suite in suites}
    suite_id = st.selectbox(
        "Suite",
        list(suite_by_id),
        index=list(suite_by_id).index("gemini-smoke") if "gemini-smoke" in suite_by_id else 0,
    )
    suite = suite_by_id[suite_id]
    target_id = st.selectbox("Target", [target.id for target in all_targets()])
    categories = st.multiselect("OWASP categories", sorted({test.owasp_category.value for test in suite.tests}))
    severity = st.multiselect("Severity", sorted({test.severity.value for test in suite.tests}))
    concurrency = st.slider("Concurrency", 1, 10, settings.max_concurrency)
    dry_run = st.checkbox("Dry run")
    selected = [
        test
        for test in suite.tests
        if (not categories or test.owasp_category.value in categories)
        and (not severity or test.severity.value in severity)
    ]
    st.metric("Selected tests", len(selected))
    authorized = st.checkbox("I confirm I am authorized to test this target.")
    if st.button("Start Execution", disabled=not authorized):
        engine = ExecutionEngine(SessionFactory, max_concurrency=concurrency)
        summary = asyncio.run(
            engine.run_suite(
                suite,
                target_by_id(target_id),
                authorization_confirmed=True,
                dry_run=dry_run,
                category_filter=set(categories) if categories else None,
            )
        )
        st.success(f"{summary.run_id}: {summary.status.value}, {summary.total_tests} tests")

elif page == "Runs":
    st.header("Runs")
    runs = query_all(TestRunRecord)
    if runs:
        df = pd.DataFrame(
            [
                {
                    "id": r.id,
                    "suite": r.suite_id,
                    "target": r.target_id,
                    "status": r.status,
                    "start": r.start_time,
                    "tests": r.total_tests,
                }
                for r in runs
            ]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
        ids = df["id"].tolist()
        if len(ids) >= 2:
            a, b = st.selectbox("Baseline", ids), st.selectbox("Current", ids, index=1)
            with SessionFactory() as session:
                previous = list(session.get(TestRunRecord, a).results)
                current = list(session.get(TestRunRecord, b).results)
            st.json(compare_runs(previous, current))
    else:
        st.info("No runs recorded.")

elif page == "Run Details":
    st.header("Run Details")
    runs = query_all(TestRunRecord)
    run_id = st.selectbox("Run", [run.id for run in runs] or [""])
    if run_id:
        with SessionFactory() as session:
            run = session.get(TestRunRecord, run_id)
            assert run is not None
            st.json(summarize_results(run.results))
            rows = [
                {
                    "test": r.test_id,
                    "category": r.owasp_category,
                    "outcome": r.outcome,
                    "severity": r.severity,
                    "prompt": r.redacted_prompt,
                    "response": r.redacted_response,
                    "reasoning": r.evaluator_reasoning,
                }
                for r in run.results
            ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

elif page == "Findings":
    st.header("Findings")
    findings = query_all(FindingRecord)
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "title": f.title,
                    "severity": f.severity,
                    "category": f.owasp_category,
                    "status": f.status,
                    "target": f.affected_target,
                    "evidence": f.evidence,
                    "remediation": f.remediation,
                }
                for f in findings
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )

elif page == "Test Library":
    st.header("Test Library")
    suites = available_suites()
    suite_by_id = {suite.id: suite for suite in suites}
    suite = suite_by_id[st.selectbox("Suite", list(suite_by_id))]
    search = st.text_input("Search")
    rows = [
        test.model_dump(mode="json")
        for test in suite.tests
        if not search or search.lower() in (test.id + test.name + test.description).lower()
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.download_button(
        "Download test template",
        data=suite.tests[0].model_dump_json(indent=2),
        file_name="promptguard-test-template.json",
    )

elif page == "Targets":
    st.header("Targets")
    st.caption("Secret values are referenced by environment variable name only and are never shown here.")
    st.dataframe(
        pd.DataFrame([target.model_dump(mode="json") for target in all_targets()]),
        use_container_width=True,
        hide_index=True,
    )

elif page == "Architecture Review":
    st.header("Architecture Review")
    suite = load_suite(Path("data/test_suites/owasp_2025_starter.yaml"))
    review_items = [test for test in suite.tests if test.assessment_mode.value == "architecture_review"]
    for item in review_items:
        with st.expander(item.name):
            st.radio("Answer", ["yes", "no", "partial", "unknown", "not applicable"], key=item.id)
            st.text_area("Evidence notes", key=item.id + "-evidence")
            st.text_area("Remediation notes", key=item.id + "-remediation")

elif page == "Settings":
    st.header("Settings")
    st.write(settings.model_dump())
    st.warning(
        "Evidence storage can contain sensitive target output. External target raw storage is disabled by default."
    )
