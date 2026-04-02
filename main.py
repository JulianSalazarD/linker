"""
Pipeline completo: extracción de archivo → inferencia con LLM.

Uso:
    python main.py <archivo> [--provider gemini|glm|minimax] [--ocr]

Ejemplos:
    python main.py "pruebas/carera 26 No 50 - 47_260318_200729.docx"
    python main.py "pruebas/Bogotá Cra 62#64-10_260327_191939.pdf" --ocr
    python main.py "pruebas/Calle 182 # 45 45_260318_201415.docx" --provider gemini
"""
from __future__ import annotations

import argparse
import json
import warnings

warnings.filterwarnings("ignore", message="Core Pydantic V1 functionality", category=UserWarning)

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

from processor.extractor import extract
from llm_client import extract_data


def run(file_path: str, provider: str = "minimax", ocr: bool = False) -> dict:
    content = extract(file_path, ocr=ocr)
    print(f"[extractor] {content.source}  texto={len(content.text)} chars  imgs={len(content.images)}")

    data = extract_data(
        text=content.text,
        file_path=content.source,
        provider=provider,
    )
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extrae y estructura datos de un documento.")
    parser.add_argument("file", help="Ruta al archivo (.docx, .pdf, …)")
    parser.add_argument("--provider", default="minimax", choices=["gemini", "glm", "minimax"],
                        help="Proveedor LLM (default: minimax)")
    parser.add_argument("--ocr", action="store_true", help="Aplicar OCR a imágenes/páginas escaneadas")
    args = parser.parse_args()

    result = run(args.file, provider=args.provider, ocr=args.ocr)
    print(json.dumps(result, ensure_ascii=False, indent=2))
