"""Cliente Gemini (Google Generative AI)."""
from __future__ import annotations

import os

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models import BaseChatModel

from llm_client.client import BaseLLMClient, register_client


class GeminiClient(BaseLLMClient):
    provider = "gemini"

    def get_llm(self, model: str) -> BaseChatModel:
        return ChatGoogleGenerativeAI(model=model, google_api_key=os.environ["GEMINI_API_KEY"])


register_client(GeminiClient())
