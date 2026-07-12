from abc import ABC, abstractmethod

from promptguard.models.schemas import AdapterResponse, EvaluationResult, TestCase


class Evaluator(ABC):
    name = "base"
    version = "0.1.0"

    @abstractmethod
    def evaluate(self, test_case: TestCase, response: AdapterResponse) -> EvaluationResult:
        raise NotImplementedError
