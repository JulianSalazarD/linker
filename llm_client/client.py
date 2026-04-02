"""
Interfaz base para clientes LLM y función principal de extracción de datos.
"""
from __future__ import annotations

import json
import sys
import warnings
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

warnings.filterwarnings("ignore", message="Core Pydantic V1 functionality", category=UserWarning)

# Asegurar que la raíz del proyecto esté en sys.path (necesario al correr como script)
_root = str(Path(__file__).parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from llm_client.config import load_config, build_schema_str, load_prompt


class BaseLLMClient(ABC):
    """Interfaz común para todos los proveedores LLM."""

    provider: str = ""  # identificador: "gemini", "glm", "minimax", …

    @abstractmethod
    def get_llm(self, model: str) -> BaseChatModel:
        """Retorna una instancia del LLM de LangChain para el modelo dado."""


# ---------------------------------------------------------------------------
# Registro
# ---------------------------------------------------------------------------

_CLIENTS: list[BaseLLMClient] = []


def register_client(client: BaseLLMClient) -> None:
    """Registra un cliente. Los últimos registrados tienen mayor prioridad."""
    _CLIENTS.insert(0, client)


def get_client(provider: str) -> BaseLLMClient:
    """Devuelve el cliente registrado para el proveedor dado."""
    for client in _CLIENTS:
        if client.provider == provider:
            return client
    registered = [c.provider for c in _CLIENTS]
    raise ValueError(f"No hay cliente registrado para: {provider!r}\nRegistrados: {registered}")


def extract_data(
    text: str,
    file_path: str,
    provider: str = "minimax",
    data_path: str = "config/data.json",
    prompt_path: str = "config/prompt.md",
) -> dict:
    """Envía el texto al LLM indicado y retorna los datos extraídos como dict."""
    config = load_config(data_path)
    schema_str = build_schema_str(config["fields"])
    model = config["models"][provider]

    prompt = load_prompt(prompt_path, schema=schema_str, file_path=file_path, text=text)

    llm = get_client(provider).get_llm(model)
    if llm is None:
        raise ValueError(f"Failed to initialize LLM for provider: {provider!r}")
    content: Any = llm.invoke([HumanMessage(content=prompt)]).content

    if isinstance(content, list):
        raw = "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    elif isinstance(content, str):
        raw = content
    elif content is None:
        raise ValueError("LLM response content is empty")
    else:
        raw = str(content)

    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)


if __name__ == "__main__":
    import json
    from dotenv import load_dotenv, find_dotenv

    load_dotenv(find_dotenv())

    for _mod in ["llm_client.gemini", "llm_client.glm", "llm_client.minimax"]:
        __import__(_mod)
    from llm_client.client import extract_data as _extract_data

    # Proveedor por argumento, por defecto minimax
    _provider = sys.argv[1] if len(sys.argv) > 1 else "minimax"
    # Archivo de prueba por argumento, por defecto el primero en pruebas/
    _fp = sys.argv[2] if len(sys.argv) > 2 else "pruebas/carera 26 No 50 - 47_260318_200729.docx"

    import processor.docx_extractor  # noqa: F401
    import processor.pdf_extractor   # noqa: F401
    from processor.extractor import extract as _extract_file

    _content = _extract_file(_fp)
    print(f"Texto extraído ({len(_content.text)} chars) de: {_fp}\n")

    _result = _extract_data(
        text=_content.text,
        file_path=_fp,
        provider=_provider,
        data_path="config/data.json",
        prompt_path="config/prompt.md",
    )
    print(json.dumps(_result, ensure_ascii=False, indent=2))


