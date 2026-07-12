from collections import Counter
from collections.abc import Iterable
from statistics import mean, median

from promptguard.repositories.database import TestResultRecord


def estimate_tokens(text: str) -> int:
    return max(1, len(text.split()) + len(text) // 16)


def estimate_cost(input_tokens: int, output_tokens: int, per_million: float = 0.15) -> float:
    return round(((input_tokens + output_tokens) / 1_000_000) * per_million, 6)


def summarize_results(results: Iterable[TestResultRecord]) -> dict[str, object]:
    items = list(results)
    outcomes = Counter(item.outcome for item in items)
    categories = Counter(item.owasp_category for item in items)
    latencies = [item.latency_ms for item in items]
    total = len(items)
    passed = outcomes.get("passed", 0)
    return {
        "total": total,
        "passed": passed,
        "failed": outcomes.get("failed", 0),
        "manual_review": outcomes.get("manual_review", 0),
        "errors": outcomes.get("error", 0),
        "skipped": outcomes.get("skipped", 0),
        "pass_rate": round(passed / total * 100, 2) if total else 0,
        "by_outcome": dict(outcomes),
        "by_category": dict(categories),
        "average_latency_ms": round(mean(latencies), 2) if latencies else 0,
        "median_latency_ms": round(median(latencies), 2) if latencies else 0,
        "p95_latency_ms": round(sorted(latencies)[int(len(latencies) * 0.95) - 1], 2) if latencies else 0,
        "input_tokens": sum(item.approximate_input_tokens for item in items),
        "output_tokens": sum(item.approximate_output_tokens for item in items),
        "estimated_cost": round(sum(item.estimated_cost for item in items), 6),
    }


def compare_runs(previous: list[TestResultRecord], current: list[TestResultRecord]) -> dict[str, object]:
    prev = {item.test_id: item.outcome for item in previous}
    curr = {item.test_id: item.outcome for item in current}
    newly_failed = [
        test_id for test_id, outcome in curr.items() if outcome == "failed" and prev.get(test_id) != "failed"
    ]
    resolved = [test_id for test_id, outcome in curr.items() if outcome != "failed" and prev.get(test_id) == "failed"]
    return {
        "newly_failed": newly_failed,
        "resolved_failures": resolved,
        "regressions": len(newly_failed),
        "improvements": len(resolved),
    }
