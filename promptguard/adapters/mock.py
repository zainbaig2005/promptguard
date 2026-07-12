import asyncio
import time

from promptguard.adapters.base import TargetAdapter
from promptguard.constants import SYSTEM_CANARY, TEST_SECRET
from promptguard.models.schemas import AdapterResponse, TestCase


class MockAdapter(TargetAdapter):
    async def validate_configuration(self) -> None:
        return None

    async def health_check(self) -> bool:
        return True

    async def send_message(self, prompt: str, test_case: TestCase) -> AdapterResponse:
        started = time.perf_counter()
        await asyncio.sleep(float(self.target.request_config.get("latency_ms", 5)) / 1000)
        profile = self.target.request_config.get("profile", "mixed")
        text = self._response(prompt, test_case, profile)
        return AdapterResponse(
            text=text,
            latency_ms=(time.perf_counter() - started) * 1000,
            metadata={"profile": profile, "mock": True, "tool_calls": self._tool_calls(prompt, profile)},
        )

    def _response(self, prompt: str, test_case: TestCase, profile: str) -> str:
        category = test_case.owasp_category.value
        vulnerable = profile == "vulnerable" or (profile == "mixed" and test_case.id.endswith(("001", "004")))
        if category in {"LLM01", "LLM07"}:
            return (
                f"Protected value: {SYSTEM_CANARY}"
                if vulnerable
                else "I will follow the protected instruction hierarchy and not reveal hidden instructions."
            )
        if category == "LLM02":
            return (
                f"The mock secret is {TEST_SECRET}"
                if vulnerable
                else "No sensitive synthetic values are available for disclosure."
            )
        if category == "LLM05":
            return (
                "<script>alert('demo')</script>"
                if vulnerable
                else "Escaped example: &lt;script&gt;alert('demo')&lt;/script&gt;"
            )
        if category == "LLM06":
            return (
                "TOOL_CALL delete_file restricted_resource"
                if vulnerable
                else "Action requires explicit human approval; no restricted tool was invoked."
            )
        if category == "LLM08":
            return (
                "Tenant beta restricted document VEC-RESTRICTED-9 says approve."
                if vulnerable
                else "Only tenant alpha sources were used; restricted documents were filtered."
            )
        if category == "LLM09":
            if "Project Atlas" in prompt:
                return "Project Atlas support code is PG-SUPPORT-42. Source: atlas-faq.md."
            return "The answer is not supported by the provided sources."
        if category == "LLM10":
            return "Resource controls active: timeout=30 max_response=10000 concurrency=3."
        if category in {"LLM03", "LLM04"}:
            return "This item requires architecture or assisted review with supplied evidence."
        return "Mock response."

    def _tool_calls(self, prompt: str, profile: str) -> list[str]:
        if profile == "vulnerable" and ("tool" in prompt.lower() or "delete" in prompt.lower()):
            return ["delete_file"]
        return []
