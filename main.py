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

        style = {"font": "Arial Nova Cond", "size": 24}
        rt.add(prefix, color="1F497D", **style)
        parts = re.split(r'(\[.*?\])', body)
        for part in parts:
            if part.startswith("[") and part.endswith("]"):
                rt.add(part[1:-1], color="FF0000", **style)
            else:
                rt.add(part, color="1F497D", **style)

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


cli = typer.Typer(rich_markup_mode="rich")


@cli.command()
def generate(
    file: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False,
        help="Ruta al archivo (.docx, .pdf, …)"),
    provider: str = typer.Option("openrouter", "--provider", "-p",
        help="Provider LLM: [cyan]gemini[/], [cyan]glm[/], [cyan]minimax[/], [cyan]openrouter[/]"),
    ocr: bool = typer.Option(False, "--ocr", "-o", help="Usar OCR"),
    confirm: bool = typer.Option(False, "--confirm", "-c",
        help="[yellow]Abrir UI de confirmación en el navegador[/]"),
    port: int = typer.Option(8000, "--port", help="Puerto para UI de confirmación"),
    output_name: str = typer.Option("DOCUMENTO PROCEDIMIENTO INSTALACIÓN", "--output-name", "-n",
        help="Nombre del documento de salida (sin extensión)"),
    output_dir: Path = typer.Option(None, "--output-dir", "-d",
        help="Directorio donde se guardará el documento (por defecto: carpeta del archivo de entrada)"),
    pdf: bool = typer.Option(False, "--pdf", help="[green]Generar también PDF[/]"),
    libreoffice: bool = typer.Option(False, "--libreoffice", "-l",
        help="Usar LibreOffice para PDF en lugar de docx2pdf (Windows)"),
):
    """[bold blue]Pipeline completo[/]: extracción de archivo → inferencia LLM → confirmación."""
    if output_dir is None:
        output_dir = file.parent

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
    from rich import print as rprint
    rprint(f"[green]DOCX generado:[/] {output_path}")
    if pdf_path:
        rprint(f"[green]PDF generado:[/] {pdf_path}")


@cli.command()
def install():
    """[bold yellow]Verificar e instalar[/] dependencias del sistema (tesseract, libreoffice)."""
    import shutil
    import platform
    import subprocess

    system = platform.system().lower()
    missing: list[str] = []
    found: list[str] = []

    # ── Tesseract ───────────────────────────────────────────────
    tess = shutil.which("tesseract")
    if tess:
        try:
            ver = subprocess.check_output([tess, "--version"], stderr=subprocess.STDOUT, text=True).split("\n")[0]
            found.append(f"tesseract  →  {ver}  ({tess})")
        except Exception:
            found.append(f"tesseract  →  {tess}")
    else:
        missing.append("tesseract")

    # ── LibreOffice (opcional, para --pdf --libreoffice) ─────────
    lo = shutil.which("libreoffice") or shutil.which("soffice")
    if lo:
        found.append(f"libreoffice  →  {lo}")
    else:
        missing.append("libreoffice (opcional, para --pdf --libreoffice)")

    # ── Reporte ─────────────────────────────────────────────────
    from rich import print as rprint

    rprint()
    if found:
        rprint("[bold green]✓ Encontrados:[/]")
        for f in found:
            rprint(f"  {f}")

    if missing:
        rprint()
        rprint("[bold red]✗ Faltan:[/]")
        for m in missing:
            rprint(f"  {m}")
        rprint()
        rprint("[bold]Instrucciones de instalación:[/]")

        if "tesseract" in missing:
            rprint()
            rprint("  [cyan]tesseract[/] (requerido para OCR):")
            if system == "linux":
                rprint("    Ubuntu/Debian:  sudo apt install tesseract-ocr tesseract-ocr-spa")
                rprint("    Arch/CachyOS:   sudo pacman -S tesseract tesseract-data-spa")
                rprint("    Fedora:         sudo dnf install tesseract tesseract-langpack-spa")
            elif system == "darwin":
                rprint("    brew install tesseract tesseract-lang")
            elif system == "windows":
                rprint("    Descargar instalador: https://github.com/UB-Mannheim/tesseract/wiki")
                rprint("    Agregar al PATH o configurar en Python:")
                rprint('    pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"')

        if any("libreoffice" in m for m in missing):
            rprint()
            rprint("  [cyan]libreoffice[/] (opcional, conversión a PDF):")
            if system == "linux":
                rprint("    Ubuntu/Debian:  sudo apt install libreoffice")
                rprint("    Arch/CachyOS:   sudo pacman -S libreoffice-still")
            elif system == "darwin":
                rprint("    brew install --cask libreoffice")
            elif system == "windows":
                rprint("    Descargar: https://www.libreoffice.org/download/")
    else:
        rprint()
        rprint("[bold green]Todas las dependencias del sistema están instaladas.[/]")

    # ── Dependencias Python ─────────────────────────────────────
    rprint()
    rprint("[bold]Dependencias Python:[/]")
    rprint("  Instalar con:  [cyan]uv pip install .[/]")
    rprint("  O bien:        [cyan]pip install .[/]")


if __name__ == "__main__":
    cli()
