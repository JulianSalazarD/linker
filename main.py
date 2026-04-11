"""
Pipeline completo: extracción de archivo → inferencia con LLM → confirmación.

Uso:
    python main.py <archivo> [-p provider] [-o] [-c] [--port 8000]
                     [-n nombre] [-d directorio] [--pdf] [-l]

Ejemplos:
    python main.py "archivo.docx"
    python main.py "archivo.pdf" --ocr --confirm
    python main.py "archivo.docx" --provider gemini --confirm
    python main.py "archivo.pdf" -n "MI INFORME" -d "salida" --pdf
"""
from __future__ import annotations

import asyncio
import json
import re
import warnings
from pathlib import Path

import typer

warnings.filterwarnings("ignore", message="Core Pydantic V1 functionality", category=UserWarning)

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

from processor.extractor import extract
from llm_client import extract_data
from products.products import build_products, flatten_cotization, parse_price, Product
from generator.template import fill_template

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


def build_richtext_fotos(confirmed_fotos: list[dict]) -> list[dict]:
    """Convierte fotos confirmadas (con base64 y caption) a RichText + PIL."""
    import base64
    from io import BytesIO
    from PIL import Image
    from docxtpl import RichText

    fotos = []
    for cap in confirmed_fotos:
        text = cap["caption"]
        image_b64 = cap["image_b64"]

        # Decodificar imagen base64 a PIL
        img_data = base64.b64decode(image_b64)
        pil_img = Image.open(BytesIO(img_data)).copy()

        rt = RichText()
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

        fotos.append({"imagen": pil_img, "pie": rt})

    return fotos


def run(file_path: str, provider: str = "minimax", ocr: bool = False) -> tuple[dict, list[Product], list[dict]]:
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

    captions = build_captions(data, len(content.images))
    fotos = build_richtext_fotos(captions)


    return data, products, fotos


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

    Product._counter = 0
    confirmed_products = []
    for p in confirmed_products_raw:
        confirmed_products.append(Product(
            qty=int(p["qty"]),
            desc=p["desc"],
            unit=p["unit"],
            vr_uni_inc=int(p["vr_uni_inc"]),
        ))

    # 7. Convertir captions + imágenes base64 a RichText + PIL
    fotos = build_richtext_fotos(confirmed_fotos_raw)

    return confirmed_data, confirmed_products, fotos


if __name__ == "__main__":
    cli = typer.Typer(rich_markup_mode="rich")

    @cli.command()
    def main(
        file: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False,
            help="Ruta al archivo (.docx, .pdf, …)"),
        provider: str = typer.Option("minimax", "--provider", "-p",
            help="Provider LLM: [cyan]gemini[/], [cyan]glm[/], [cyan]minimax[/]"),
        ocr: bool = typer.Option(False, "--ocr", "-o", help="Usar OCR"),
        confirm: bool = typer.Option(False, "--confirm", "-c",
            help="[yellow]Abrir UI de confirmación en el navegador[/]"),
        port: int = typer.Option(8000, "--port", help="Puerto para UI de confirmación"),
        output_name: str = typer.Option("DOCUMENTO PROCEDIMIENTO INSTALACIÓN", "--output-name", "-n",
            help="Nombre del documento de salida (sin extensión)"),
        output_dir: Path = typer.Option(Path("pruebas"), "--output-dir", "-d",
            help="Directorio donde se guardará el documento"),
        pdf: bool = typer.Option(False, "--pdf", help="[green]Generar también PDF[/]"),
        libreoffice: bool = typer.Option(False, "--libreoffice", "-l",
            help="Usar LibreOffice para PDF en lugar de docx2pdf (Windows)"),
    ):
        """[bold blue]Pipeline completo[/]: extracción de archivo → inferencia LLM → confirmación."""
        if confirm:
            result_data, result_products, result_fotos = asyncio.run(
                run_with_confirm(str(file), provider, ocr, port)
            )
        else:
            result_data, result_products, fotos = run(str(file), provider=provider, ocr=ocr)
            result_fotos = []

        print(json.dumps(result_data, ensure_ascii=False, indent=2))
        for p in result_products:
            print(p)

        output_path, pdf_path = fill_template(
            result_data,
            result_products,
            output_dir=str(output_dir),
            output_name=output_name,
            fotos=result_fotos,
            generate_pdf=pdf,
            prefer_libreoffice=libreoffice,
        )
        typer.echo(f"[green]DOCX generado:[/] {output_path}")
        if pdf_path:
            typer.echo(f"[green]PDF generado:[/] {pdf_path}")

    cli()
