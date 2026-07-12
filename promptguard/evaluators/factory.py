from typing import Protocol

from promptguard.evaluators.deterministic import (
    ContainsEvaluator,
    ExactMatchEvaluator,
    JsonSchemaEvaluator,
    KnownAnswerEvaluator,
    ManualReviewEvaluator,
    MustNotContainEvaluator,
    OutputRiskEvaluator,
    RefusalBoundaryEvaluator,
    RegexEvaluator,
    ResourceLimitEvaluator,
    ToolCallEvaluator,
)
from promptguard.models.schemas import AdapterResponse, EvaluationResult, TestCase


class SupportsEvaluate(Protocol):
    def evaluate(self, test_case: TestCase, response: AdapterResponse) -> EvaluationResult: ...


EVALUATORS: dict[str, SupportsEvaluate] = {
    "contains": ContainsEvaluator(),
    "must_not_contain": MustNotContainEvaluator(),
    "regex": RegexEvaluator(),
    "exact_match": ExactMatchEvaluator(),
    "json_schema": JsonSchemaEvaluator(),
    "refusal_boundary": RefusalBoundaryEvaluator(),
    "output_risk": OutputRiskEvaluator(),
    "tool_call": ToolCallEvaluator(),
    "known_answer": KnownAnswerEvaluator(),
    "resource_limit": ResourceLimitEvaluator(),
    "manual_review": ManualReviewEvaluator(),
}


class CompositeEvaluator:
    name = "composite"

    def evaluate(self, test_case: TestCase, response: AdapterResponse) -> EvaluationResult:
        configured = test_case.evaluator.config.get("evaluators") or [test_case.expected_behavior.type]
        results = [EVALUATORS.get(name, ManualReviewEvaluator()).evaluate(test_case, response) for name in configured]
        failed = [item for item in results if item.outcome == "failed"]
        if failed:
            return failed[0]
        return results[0]


def evaluate_response(test_case: TestCase, response: AdapterResponse) -> EvaluationResult:
    evaluator = (
        CompositeEvaluator()
        if test_case.evaluator.type == "composite"
        else EVALUATORS.get(test_case.evaluator.type, ManualReviewEvaluator())
    )
    return evaluator.evaluate(test_case, response)
