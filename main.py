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
import re
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message="Core Pydantic V1 functionality", category=UserWarning)

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

from processor.extractor import extract
from llm_client import extract_data
from products.products import build_products, flatten_cotization, parse_price, Product


def run(file_path: str, provider: str = "minimax", ocr: bool = False) -> tuple[dict, list[Product]]:
    content = extract(file_path, ocr=ocr)
    print(f"[extractor] {content.source}  texto={len(content.text)} chars  imgs={len(content.images)}")

    data = extract_data(
        text=content.text,
        file_path=content.source,
        provider=provider,
    )

    print("[LLM PROVIDER DATA] Datos extraídos")

    flat_config_path = flatten_cotization()
    price_flat = extract_data(
        text=content.text,
        file_path=content.source,
        provider=provider,
        data_path=flat_config_path,
        prompt_path="config/prompt_cotizacion.md",
    )
    Path(flat_config_path).unlink(missing_ok=True)

    price = parse_price(price_flat)
    products = build_products(price)

    return data, products


def build_captions(data: dict, total_images: int) -> list[dict]:
    """Genera pies de foto iniciales desde config/images.json."""
    with open("config/images.json", encoding="utf-8") as f:
        captions_cfg = json.load(f)

    apartamento = str(data.get("apartamento", "") or "")
    captions = []

    for i in range(total_images):
        if i == 0:
            key = "1"
        elif i == total_images - 1:
            key = "final"
        else:
            key = "n"

        text = captions_cfg[key].replace("{{ apartamento }}", apartamento)
        caption = f"Ilustración {i + 1}. {text}"
        captions.append({"index": i, "caption": caption})

    return captions


def build_richtext_fotos(images: list, confirmed_captions: list[dict]) -> list[dict]:
    """Convierte captions de texto plano a RichText con colores."""
    from docxtpl import RichText

    fotos = []
    for cap in confirmed_captions:
        idx = cap["index"]
        text = cap["caption"]

        rt = RichText()
        # Separar prefijo "Ilustración N. " del resto
        match = re.match(r"(Ilustración \d+\.\s*)(.*)", text, re.IGNORECASE)
        if match:
            prefix, body = match.group(1), match.group(2)
        else:
            prefix, body = "", text

        rt.add(prefix, color="1F497D")
        parts = re.split(r'(\[.*?\])', body)
        for part in parts:
            if part.startswith("[") and part.endswith("]"):
                rt.add(part[1:-1], color="FF0000")
            else:
                rt.add(part, color="1F497D")

        fotos.append({"imagen": images[idx], "pie": rt})

    return fotos


async def run_with_confirm(file_path: str, provider: str, ocr: bool, port: int):
    from confirmer.app import main_async

    # 1. Extraer contenido
    content = extract(file_path, ocr=ocr)
    print(f"[extractor] {content.source}  texto={len(content.text)} chars  imgs={len(content.images)}")

    # 2. Inferencia LLM: datos del cliente
    data = extract_data(
        text=content.text,
        file_path=content.source,
        provider=provider,
    )
    print("[LLM] Datos extraídos")

    # 3. Inferencia LLM: productos/cotización
    flat_config_path = flatten_cotization()
    price_flat = extract_data(
        text=content.text,
        file_path=content.source,
        provider=provider,
        data_path=flat_config_path,
        prompt_path="config/prompt_cotizacion.md",
    )
    Path(flat_config_path).unlink(missing_ok=True)
    price = parse_price(price_flat)
    products = build_products(price)
    print("[LLM] Productos extraídos")

    # 4. Generar captions iniciales
    captions = build_captions(data, len(content.images))

    # 5. Abrir UI de confirmación
    result = await main_async(content, data, products, captions, port)

    # 6. Reconstruir Product objects desde dicts confirmados
    confirmed_data = result["data"]
    confirmed_products_raw = result["products"]
    confirmed_fotos_raw = result["fotos"]

    GenProduct.reset_counter()
    confirmed_products = []
    for p in confirmed_products_raw:
        confirmed_products.append(GenProduct(
            qty=int(p["qty"]),
            desc=p["desc"],
            unit=p["unit"],
            vr_uni_inc=int(p["vr_uni_inc"]),
        ))

    # 7. Convertir captions a RichText
    fotos = build_richtext_fotos(content.images, confirmed_fotos_raw)

    return confirmed_data, confirmed_products, fotos


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extrae y estructura datos de un documento.")
    parser.add_argument("file", help="Ruta al archivo (.docx, .pdf, …)")
    parser.add_argument("--provider", default="minimax", choices=["gemini", "glm", "minimax"])
    parser.add_argument("--ocr", action="store_true")
    parser.add_argument("--confirm", action="store_true", help="Abrir UI de confirmación en el navegador")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.confirm:
        result_data, result_products, result_fotos = asyncio.run(
            run_with_confirm(args.file, args.provider, args.ocr, args.port)
        )
    else:
        result_data, result_products = run(args.file, provider=args.provider, ocr=args.ocr)
        result_fotos = []

    print(json.dumps(result_data, ensure_ascii=False, indent=2))
    for p in result_products:
        print(p)
