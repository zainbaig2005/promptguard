from __future__ import annotations

import asyncio
from html import escape
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.io as pio
import streamlit as st
from sqlalchemy import select

from promptguard.config import get_settings
from promptguard.demo import seed_demo_sync
from promptguard.exceptions import PromptGuardError
from promptguard.execution.engine import ExecutionEngine
from promptguard.models.schemas import TestSuite
from promptguard.repositories.database import FindingRecord, TestResultRecord, TestRunRecord, init_database
from promptguard.services.metrics import compare_runs, summarize_results
from promptguard.target_loader import all_targets, target_by_id
from promptguard.test_loader import load_suite, load_suites

st.set_page_config(page_title="PromptGuard", page_icon="PG", layout="wide")
st.markdown(
    """
    <style>
    :root {
      --pg-ink: #0d1821;
      --pg-muted: #5f6f7c;
      --pg-line: #d8e0e8;
      --pg-soft: #f5f8fb;
      --pg-panel: #ffffff;
      --pg-primary: #0f766e;
      --pg-primary-soft: #d9f3ef;
    }
    .stApp { background: #f4f7fa; color: var(--pg-ink); }
    header[data-testid="stHeader"] {
      height: 0 !important;
      background: transparent !important;
    }
    header[data-testid="stHeader"] * { display: none !important; }
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"] {
      display: none !important;
    }
    [data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid var(--pg-line); }
    [data-testid="stSidebar"] * { color: var(--pg-ink) !important; }
    [data-testid="stSidebar"] [role="radiogroup"] label {
      border-radius: 6px; padding: .35rem .5rem; margin: .1rem 0;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:hover { background: var(--pg-soft); }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: var(--pg-muted) !important; }
    .block-container { padding-top: 1.35rem; padding-bottom: 3rem; max-width: 1440px; }
    .pg-topbar {
      display: flex; align-items: center; justify-content: space-between;
      padding: .75rem 0 1.1rem; border-bottom: 1px solid var(--pg-line); margin-bottom: 1.1rem;
    }
    .pg-brand { display: flex; align-items: center; gap: .7rem; }
    .pg-logo {
      width: 34px; height: 34px; display: grid; place-items: center; border-radius: 7px;
      background: var(--pg-primary); color: white; font-weight: 800;
      letter-spacing: 0;
    }
    .pg-wordmark { font-size: 1.35rem; font-weight: 800; color: var(--pg-ink); letter-spacing: 0; }
    .pg-subtle { color: var(--pg-muted); font-size: .86rem; }
    .pg-header { margin: .85rem 0 1.15rem; }
    .pg-kicker { color: var(--pg-primary); font-size: .78rem; font-weight: 800; text-transform: uppercase; }
    .pg-title { color: var(--pg-ink); font-size: 1.85rem; line-height: 1.15; font-weight: 800; margin-top: .2rem; }
    .pg-card {
      background: var(--pg-panel); border: 1px solid var(--pg-line); border-radius: 8px;
      padding: 1rem 1rem .85rem; box-shadow: 0 4px 18px rgba(16, 25, 35, .04);
    }
    .pg-metric-label { color: var(--pg-muted); font-size: .76rem; font-weight: 800; text-transform: uppercase; }
    .pg-metric-value { color: var(--pg-ink); font-size: 1.55rem; line-height: 1.35; font-weight: 850; }
    .pg-metric-accent {
      width: 34px; height: 3px; border-radius: 999px; margin-top: .55rem; background: var(--pg-primary);
    }
    .pg-callout {
      background: #fff; border: 1px solid var(--pg-line); border-left: 4px solid var(--pg-primary);
      border-radius: 7px; padding: .85rem 1rem; color: var(--pg-muted);
    }
    .pg-section-card {
      background: var(--pg-panel); border: 1px solid var(--pg-line); border-radius: 8px;
      padding: .8rem .9rem; box-shadow: 0 4px 18px rgba(16, 25, 35, .04);
    }
    div[data-testid="stDataFrame"] { border: 1px solid var(--pg-line); border-radius: 8px; overflow: hidden; }
    label,
    [data-testid="stWidgetLabel"] p {
      color: var(--pg-muted) !important;
      font-weight: 650 !important;
    }
    [data-baseweb="select"] > div,
    [data-baseweb="input"] > div,
    [data-baseweb="tag"] {
      border-radius: 6px !important;
    }
    [data-baseweb="select"] > div {
      background-color: #ffffff !important;
      border: 1px solid var(--pg-line) !important;
      color: var(--pg-ink) !important;
      box-shadow: none !important;
      min-height: 44px;
    }
    [data-baseweb="select"] span,
    [data-baseweb="select"] input {
      color: var(--pg-ink) !important;
    }
    [data-baseweb="select"] svg {
      color: var(--pg-muted) !important;
      fill: var(--pg-muted) !important;
    }
    [data-baseweb="popover"] [role="listbox"],
    [data-baseweb="popover"] [role="option"] {
      background-color: #ffffff !important;
      color: var(--pg-ink) !important;
    }
    [data-baseweb="popover"] [role="option"]:hover {
      background-color: var(--pg-soft) !important;
    }
    .stButton > button, .stDownloadButton > button {
      border-radius: 6px; border: 1px solid var(--pg-primary); background: var(--pg-primary); color: #fff;
      font-weight: 750;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
      border-color: #0b5e58; background: #0b5e58; color: #fff;
    }
    .stButton > button:disabled { background: #d8e0e8; border-color: #d8e0e8; color: #607080; }
    </style>
    """,
    unsafe_allow_html=True,
)

pio.templates["promptguard"] = pio.templates["plotly_white"]
pio.templates["promptguard"].layout.colorway = ["#0f766e", "#6b7280", "#94a3b8", "#cbd5e1"]
pio.templates.default = "promptguard"

st.markdown(
    """
    <div class="pg-topbar">
      <div class="pg-brand">
        <div class="pg-logo">PG</div>
        <div>
          <div class="pg-wordmark">PromptGuard</div>
          <div class="pg-subtle">AI security validation dashboard</div>
        </div>
      </div>
      <div class="pg-subtle">OWASP LLM 2025 mapped</div>
    </div>
    """,
    unsafe_allow_html=True,
)

settings = get_settings()
SessionFactory = init_database(settings.database_url)


def query_all(model):
    with SessionFactory() as session:
        return list(session.scalars(select(model)).all())


def available_suites() -> list[TestSuite]:
    return load_suites(Path("data/test_suites"))


def page_header(title: str, kicker: str = "PromptGuard") -> None:
    st.markdown(
        f"""
        <div class="pg-header">
          <div class="pg-kicker">{escape(kicker)}</div>
          <div class="pg-title">{escape(title)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: object, accent: str = "") -> None:
    st.markdown(
        f"""
        <div class="pg-card">
          <div class="pg-metric-label">{escape(label)}</div>
          <div class="pg-metric-value">{escape(str(value))}</div>
          <div class="pg-metric-accent"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def style_figure(fig):
    fig.update_layout(
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font={"color": "#334155", "family": "Inter, Arial, sans-serif"},
        title={"font": {"color": "#0d1821", "size": 16}, "x": 0.02, "xanchor": "left"},
        margin={"l": 40, "r": 24, "t": 58, "b": 42},
        legend_title_text="",
        legend={"font": {"color": "#475569"}},
        height=390,
    )
    axis_text = {"color": "#475569"}
    fig.update_xaxes(
        gridcolor="#eef2f6",
        linecolor="#d8e0e8",
        zerolinecolor="#d8e0e8",
        tickfont=axis_text,
        title_font=axis_text,
    )
    fig.update_yaxes(
        gridcolor="#eef2f6",
        linecolor="#d8e0e8",
        zerolinecolor="#d8e0e8",
        tickfont=axis_text,
        title_font=axis_text,
    )
    fig.update_traces(marker_line_width=0)
    return fig


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
    page_header("Security Validation Overview", "Executive view")
    runs = query_all(TestRunRecord)
    results = query_all(TestResultRecord)
    runs_desc = sorted(runs, key=lambda run: run.start_time, reverse=True)
    target_options = ["All targets", *sorted({run.target_id for run in runs_desc})]
    suite_options = ["All suites", *sorted({run.suite_id for run in runs_desc})]
    filter_cols = st.columns([1.1, 1.1, 1.2, 1.4])
    with filter_cols[0]:
        selected_target = st.selectbox("Target filter", target_options)
    with filter_cols[1]:
        selected_suite = st.selectbox("Suite filter", suite_options)

    matching_runs = [
        run
        for run in runs_desc
        if (selected_target == "All targets" or run.target_id == selected_target)
        and (selected_suite == "All suites" or run.suite_id == selected_suite)
    ]
    with filter_cols[2]:
        run_scope = st.selectbox("Run scope", ["Latest matching run", "All matching runs", "Specific run"])
    with filter_cols[3]:
        selected_run_id = ""
        if run_scope == "Specific run" and matching_runs:
            selected_run_id = st.selectbox("Run", [run.id for run in matching_runs])
        elif matching_runs:
            st.selectbox("Run", [matching_runs[0].id], disabled=True)
        else:
            st.selectbox("Run", ["No matching runs"], disabled=True)

    if run_scope == "Latest matching run":
        active_runs = matching_runs[:1]
    elif run_scope == "Specific run":
        active_runs = [run for run in matching_runs if run.id == selected_run_id]
    else:
        active_runs = matching_runs

    active_run_ids = {run.id for run in active_runs}
    filtered_results = [result for result in results if result.run_id in active_run_ids]
    metrics = summarize_results(filtered_results)
    st.caption(f"Showing {len(filtered_results)} result(s) from {len(active_runs)} run(s).")
    cols = st.columns(6)
    cards = [
        ("Total Results", metrics["total"], ""),
        ("Pass Rate", f"{metrics['pass_rate']}%", ""),
        ("Failed", metrics["failed"], ""),
        ("Manual Review", metrics["manual_review"], ""),
        ("Errors", metrics["errors"], ""),
        ("Estimated Cost", f"${metrics['estimated_cost']}", ""),
    ]
    for col, (label, value, accent) in zip(cols, cards, strict=False):
        with col:
            metric_card(label, value, accent)
    if filtered_results:
        df = pd.DataFrame(
            [
                {
                    "category": r.owasp_category,
                    "outcome": r.outcome,
                    "severity": r.severity,
                    "latency": r.latency_ms,
                    "test": r.test_id,
                }
                for r in filtered_results
            ]
        )
        left, right = st.columns(2)
        outcome_colors = {
            "passed": "#0f766e",
            "failed": "#64748b",
            "manual_review": "#94a3b8",
            "error": "#cbd5e1",
        }
        severity_colors = {"high": "#0f766e", "medium": "#64748b", "low": "#94a3b8"}
        outcome_fig = px.histogram(
            df,
            x="category",
            color="outcome",
            title="Outcomes by Category",
            color_discrete_map=outcome_colors,
        )
        severity_fig = px.histogram(
            df,
            x="severity",
            color="severity",
            title="Findings by Severity",
            color_discrete_map=severity_colors,
        )
        latency_fig = px.box(
            df,
            x="category",
            y="latency",
            title="Latency Distribution",
            color_discrete_sequence=["#0f766e"],
        )
        left.plotly_chart(style_figure(outcome_fig), width="stretch")
        right.plotly_chart(style_figure(severity_fig), width="stretch")
        st.plotly_chart(style_figure(latency_fig), width="stretch")
    else:
        st.markdown(
            '<div class="pg-callout">No results recorded yet. Seed demo data or run an authorized suite.</div>',
            unsafe_allow_html=True,
        )
    if st.button("Seed Demo Data"):
        seed_demo_sync()
        st.rerun()

elif page == "Run Tests":
    page_header("Run Tests", "Authorized execution")
    suites = available_suites()
    suite_by_id = {suite.id: suite for suite in suites}
    suite_id = st.selectbox(
        "Suite",
        list(suite_by_id),
        index=list(suite_by_id).index("gemini-smoke") if "gemini-smoke" in suite_by_id else 0,
    )
    suite = suite_by_id[suite_id]
    left, right = st.columns([1.15, 1])
    with left:
        target_id = st.selectbox("Target", [target.id for target in all_targets()])
        categories = st.multiselect("OWASP categories", sorted({test.owasp_category.value for test in suite.tests}))
        severity = st.multiselect("Severity", sorted({test.severity.value for test in suite.tests}))
    with right:
        concurrency = st.slider("Concurrency", 1, 10, 1 if target_id == "gemini-free" else settings.max_concurrency)
        dry_run = st.checkbox("Dry run")
    selected = [
        test
        for test in suite.tests
        if (not categories or test.owasp_category.value in categories)
        and (not severity or test.severity.value in severity)
    ]
    metric_card("Selected Tests", len(selected), "")
    authorized = st.checkbox("I confirm I am authorized to test this target.")
    if st.button("Start Execution", disabled=not authorized):
        engine = ExecutionEngine(SessionFactory, max_concurrency=concurrency)
        try:
            summary = asyncio.run(
                engine.run_suite(
                    suite,
                    target_by_id(target_id),
                    authorization_confirmed=True,
                    dry_run=dry_run,
                    category_filter=set(categories) if categories else None,
                )
            )
        except PromptGuardError as exc:
            st.error(str(exc))
            st.info(
                "Set the required API key in the terminal before starting Streamlit, or add it to a local .env file."
            )
        else:
            st.success(f"{summary.run_id}: {summary.status.value}, {summary.total_tests} tests")

elif page == "Runs":
    page_header("Runs", "Run history")
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
        st.dataframe(df, width="stretch", hide_index=True)
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
    page_header("Run Details", "Evidence review")
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
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

elif page == "Findings":
    page_header("Findings", "Open risk view")
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
        width="stretch",
        hide_index=True,
    )

elif page == "Test Library":
    page_header("Test Library", "Test catalog")
    suites = available_suites()
    suite_by_id = {suite.id: suite for suite in suites}
    suite = suite_by_id[st.selectbox("Suite", list(suite_by_id))]
    search = st.text_input("Search")
    rows = [
        test.model_dump(mode="json")
        for test in suite.tests
        if not search or search.lower() in (test.id + test.name + test.description).lower()
    ]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.download_button(
        "Download test template",
        data=suite.tests[0].model_dump_json(indent=2),
        file_name="promptguard-test-template.json",
    )

elif page == "Targets":
    page_header("Targets", "Configured systems")
    st.caption("Secret values are referenced by environment variable name only and are never shown here.")
    st.dataframe(
        pd.DataFrame([target.model_dump(mode="json") for target in all_targets()]),
        width="stretch",
        hide_index=True,
    )

elif page == "Architecture Review":
    page_header("Architecture Review", "Questionnaires")
    suite = load_suite(Path("data/test_suites/owasp_2025_starter.yaml"))
    review_items = [test for test in suite.tests if test.assessment_mode.value == "architecture_review"]
    for item in review_items:
        with st.expander(item.name):
            st.radio("Answer", ["yes", "no", "partial", "unknown", "not applicable"], key=item.id)
            st.text_area("Evidence notes", key=item.id + "-evidence")
            st.text_area("Remediation notes", key=item.id + "-remediation")

elif page == "Settings":
    page_header("Settings", "Runtime configuration")
    st.write(settings.model_dump())
    st.warning(
        "Evidence storage can contain sensitive target output. External target raw storage is disabled by default."
    )
