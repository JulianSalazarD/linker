"""Cliente OpenRouter (via endpoint compatible con OpenAI)."""
from __future__ import annotations

import os

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from llm_client.client import BaseLLMClient, register_client


class OpenRouterClient(BaseLLMClient):
    provider = "openrouter"

    def get_llm(self, model: str) -> BaseChatModel:
        return ChatOpenAI(
            model=model,
            api_key=SecretStr(os.environ["OPENROUTER_API_KEY"]),
            base_url="https://openrouter.ai/api/v1",
            timeout=60,
        )


register_client(OpenRouterClient())
