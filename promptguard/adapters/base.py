from abc import ABC, abstractmethod

from promptguard.models.schemas import AdapterResponse, Target, TestCase


class TargetAdapter(ABC):
    def __init__(self, target: Target) -> None:
        self.target = target

    @abstractmethod
    async def validate_configuration(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def send_message(self, prompt: str, test_case: TestCase) -> AdapterResponse:
        raise NotImplementedError

    async def send_conversation(self, prompts: list[str], test_case: TestCase) -> AdapterResponse:
        response: AdapterResponse | None = None
        for prompt in prompts:
            response = await self.send_message(prompt, test_case)
        if response is None:
            return AdapterResponse(text="", latency_ms=0)
        return response

    async def reset_conversation(self) -> None:
        return None

    async def collect_metadata(self) -> dict[str, object]:
        return {"adapter_type": self.target.adapter_type, "target_id": self.target.id}

    async def close(self) -> None:
        return None
