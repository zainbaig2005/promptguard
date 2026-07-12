from urllib.parse import urlparse

import httpx

from promptguard.adapters.base import TargetAdapter
from promptguard.exceptions import AdapterError
from promptguard.models.schemas import AdapterResponse, TestCase


class GenericRestAdapter(TargetAdapter):
    async def validate_configuration(self) -> None:
        if not self.target.base_url:
            raise AdapterError("base_url is required")
        parsed = urlparse(self.target.base_url)
        if parsed.scheme not in {"http", "https"}:
            raise AdapterError("Only http and https URLs are allowed")

    async def health_check(self) -> bool:
        await self.validate_configuration()
        return True

    async def send_message(self, prompt: str, test_case: TestCase) -> AdapterResponse:
        await self.validate_configuration()
        config = self.target.request_config
        body = dict(config.get("body_template", {}))
        body[config.get("prompt_field", "prompt")] = prompt
        method = str(config.get("method", "POST")).upper()
        if method not in {"POST", "PUT"}:
            raise AdapterError("Generic REST adapter only allows POST or PUT")
        async with httpx.AsyncClient(timeout=float(config.get("timeout", test_case.timeout_seconds))) as client:
            response = await client.request(method, self.target.base_url or "", json=body)
        response.raise_for_status()
        data = response.json()
        path = str(config.get("response_path", "response")).split(".")
        value: object = data
        for part in path:
            value = value[part] if isinstance(value, dict) else ""
        return AdapterResponse(
            text=str(value),
            latency_ms=response.elapsed.total_seconds() * 1000,
            metadata={"status_code": response.status_code},
        )
