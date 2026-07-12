import os

import httpx

from promptguard.adapters.base import TargetAdapter
from promptguard.exceptions import AdapterError
from promptguard.models.schemas import AdapterResponse, TestCase


class OpenAICompatibleAdapter(TargetAdapter):
    async def validate_configuration(self) -> None:
        if not self.target.base_url:
            raise AdapterError("base_url is required")
        if self.target.authentication_ref and not os.getenv(self.target.authentication_ref):
            raise AdapterError(f"Missing API key environment variable: {self.target.authentication_ref}")

    async def health_check(self) -> bool:
        await self.validate_configuration()
        return True

    async def send_message(self, prompt: str, test_case: TestCase) -> AdapterResponse:
        await self.validate_configuration()
        headers = {"Content-Type": "application/json"}
        if self.target.authentication_ref:
            headers["Authorization"] = f"Bearer {os.environ[self.target.authentication_ref]}"
        payload = {
            "model": self.target.model_name,
            "messages": [
                {"role": "system", "content": self.target.request_config.get("system_prompt", "")},
                {"role": "user", "content": prompt},
            ],
            "temperature": self.target.request_config.get("temperature", 0),
            "max_tokens": self.target.request_config.get("max_tokens", 512),
            **self.target.request_config.get("extra_request_fields", {}),
        }
        timeout = float(self.target.request_config.get("timeout", test_case.timeout_seconds))
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                str(self.target.base_url).rstrip("/") + "/chat/completions", headers=headers, json=payload
            )
        response.raise_for_status()
        data = response.json()
        return AdapterResponse(
            text=data["choices"][0]["message"]["content"],
            latency_ms=response.elapsed.total_seconds() * 1000,
            metadata={"provider": "openai-compatible"},
        )
