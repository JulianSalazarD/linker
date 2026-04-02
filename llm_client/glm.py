"""Cliente GLM (Zhipu AI via endpoint compatible con Anthropic)."""
from __future__ import annotations

import os

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from pydantic import SecretStr

from llm_client.client import BaseLLMClient, register_client


class GlmClient(BaseLLMClient):
    provider = "glm"

    def get_llm(self, model: str) -> BaseChatModel:
        return ChatAnthropic(
            model_name=model,
             api_key=SecretStr(os.environ["ZHIPU_API_KEY"]),
            base_url="https://open.bigmodel.cn/api/paas/v4/",
            timeout=60,
            stop=None,
        )


register_client(GlmClient())
