from promptguard.adapters.base import TargetAdapter
from promptguard.adapters.mock import MockAdapter
from promptguard.adapters.openai_compatible import OpenAICompatibleAdapter
from promptguard.adapters.rest import GenericRestAdapter
from promptguard.exceptions import AdapterError
from promptguard.models.schemas import Target


def create_adapter(target: Target) -> TargetAdapter:
    if target.adapter_type == "mock":
        return MockAdapter(target)
    if target.adapter_type == "openai-compatible":
        return OpenAICompatibleAdapter(target)
    if target.adapter_type == "generic-rest":
        return GenericRestAdapter(target)
    raise AdapterError(f"Unsupported adapter type: {target.adapter_type}")
