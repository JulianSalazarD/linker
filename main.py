"""
Pipeline completo: extracción de archivo → inferencia con LLM → confirmación.

Uso:
    python main.py <archivo> [--provider gemini|glm|minimax] [--ocr] [--confirm] [--port 8000]

Ejemplos:
    python main.py "pruebas/carera 26 No 50 - 47_260318_200729.docx"
    python main.py "pruebas/Bogotá Cra 62#64-10_260327_191939.pdf" --ocr --confirm
    python main.py "pruebas/Calle 182 # 45 45_260318_201415.docx" --provider gemini --confirm
"""
from __future__ import annotations

import argparse
import asyncio
import json
import warnings

warnings.filterwarnings("ignore", message="Core Pydantic V1 functionality", category=UserWarning)

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

from processor.extractor import extract
from llm_client import extract_data


def run(file_path: str, provider: str = "minimax", ocr: bool = False) -> tuple[dict, dict]:
    content = extract(file_path, ocr=ocr)
    print(f"[extractor] {content.source}  texto={len(content.text)} chars  imgs={len(content.images)}")

    data = extract_data(
        text=content.text,
        file_path=content.source,
        provider=provider,
    )

    print("[LLM PROVIDER DATA] Datos extraídos")

    price = extract_data(
        text=content.text,
        file_path=content.source,
        provider=provider,
        data_path="config/cotization.json",
        prompt_path="config/prompt_cotizacion.md",
    )


    return data, price


async def run_with_confirm(file_path: str, provider: str, ocr: bool, port: int) -> dict:
    from confirmer.app import main_async
    return await main_async(file_path, provider=provider, ocr=ocr, port=port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extrae y estructura datos de un documento.")
    parser.add_argument("file", help="Ruta al archivo (.docx, .pdf, …)")
    parser.add_argument("--provider", default="minimax", choices=["gemini", "glm", "minimax"])
    parser.add_argument("--ocr", action="store_true")
    parser.add_argument("--confirm", action="store_true", help="Abrir UI de confirmación en el navegador")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.confirm:
        result_data, result_price = asyncio.run(run_with_confirm(args.file, args.provider, args.ocr, args.port))
    else:
        result_data, result_price = run(args.file, provider=args.provider, ocr=args.ocr)

    print(json.dumps(result_data, ensure_ascii=False, indent=2))
    print(json.dumps(result_price, ensure_ascii=False, indent=2))
