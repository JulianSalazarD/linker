"""
UI de confirmación de datos extraídos — wizard de 3 pasos.

Uso (standalone):
    python confirmer/app.py <archivo> [--provider minimax] [--ocr] [--port 8000]
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import sys
import threading
import warnings
import webbrowser
from pathlib import Path

import uvicorn

warnings.filterwarnings("ignore", message="Core Pydantic V1 functionality", category=UserWarning)

_root = str(Path(__file__).parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from jinja2 import Environment, FileSystemLoader
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from processor.extractor import SourceContent, extract
from confirmer.viewer import docx_to_html, get_viewer_type, images_to_b64

# ---------------------------------------------------------------------------
# Estado global de la sesión (una sesión a la vez)
# ---------------------------------------------------------------------------

_content: SourceContent | None = None
_data: dict = {}
_products_dicts: list[dict] = []
_captions: list[dict] = []
_result: dict = {}
_shutdown_event = threading.Event()

# ---------------------------------------------------------------------------
# App FastAPI
# ---------------------------------------------------------------------------

_here = Path(__file__).parent

app = FastAPI()
app.mount("/static", StaticFiles(directory=str(_here / "static")), name="static")

_jinja_env = Environment(loader=FileSystemLoader(str(_here / "templates")), autoescape=True)
_jinja_env.filters["basename"] = lambda p: Path(p).name


def _load_caption_templates() -> dict:
    cfg_path = Path(_root) / "config" / "images.json"
    if cfg_path.exists():
        with open(cfg_path, encoding="utf-8") as f:
            return json.load(f)
    return {}


@app.get("/")
async def index():
    assert _content is not None
    initial = json.dumps({
        "data": _data,
        "products": _products_dicts,
        "captions": _captions,
        "caption_templates": _load_caption_templates(),
    }, ensure_ascii=False)
    html = _jinja_env.get_template("index.html").render(
        viewer_type=get_viewer_type(_content),
        text=_content.text,
        source=_content.source,
        initial_json=initial,
    )
    return HTMLResponse(html)


@app.get("/document")
async def document():
    assert _content is not None
    if "wordprocessingml" in _content.mime_type:
        return HTMLResponse(docx_to_html(_content.source))
    data = Path(_content.source).read_bytes()
    return Response(content=data, media_type=_content.mime_type,
                    headers={"Content-Disposition": "inline; filename=document.pdf"})


@app.get("/images")
async def images():
    assert _content is not None
    return JSONResponse({"images": images_to_b64(_content, thumbnail=True)})


@app.get("/images/full")
async def images_full():
    assert _content is not None
    return JSONResponse({"images": images_to_b64(_content, thumbnail=False)})


@app.get("/overlays")
async def overlays():
    overlays_dir = Path(_root) / "config" / "overlays"
    result = []
    if overlays_dir.exists():
        for f in sorted(overlays_dir.iterdir()):
            if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
                data = base64.b64encode(f.read_bytes()).decode()
                mime = "image/png" if f.suffix.lower() == ".png" else "image/jpeg"
                result.append({"name": f.stem, "data": data, "mime": mime})
    return JSONResponse({"overlays": result})


_server: uvicorn.Server | None = None


@app.post("/confirm/data")
async def confirm_data(request: Request):
    body = await request.json()
    _result["data"] = body.get("fields", {})
    return JSONResponse({"ok": True})


@app.post("/confirm/products")
async def confirm_products(request: Request):
    body = await request.json()
    _result["products"] = body.get("products", [])
    return JSONResponse({"ok": True})


@app.post("/confirm/photos")
async def confirm_photos(request: Request):
    body = await request.json()
    _result["fotos"] = body.get("fotos", [])
    _shutdown_event.set()
    return JSONResponse({"ok": True})


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

def run_server(port: int):
    global _server
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    _server = uvicorn.Server(config)
    _server.run()


async def main_async(
    content: SourceContent,
    data: dict,
    products: list,
    captions: list[dict],
    port: int = 8000,
) -> dict:
    global _content, _data, _products_dicts, _captions, _result

    _shutdown_event.clear()
    _result = {}

    _content = content
    _data = data
    _captions = captions

    # Serializar products a dicts para el frontend
    _products_dicts = [
        {"item": p.item, "qty": p.qty, "desc": p.desc, "unit": p.unit, "vr_uni_inc": p.vr_uni_inc}
        for p in products
    ]

    t = threading.Thread(target=run_server, args=(port,), daemon=True)
    t.start()

    url = f"http://127.0.0.1:{port}"
    print(f"Abriendo {url}")
    webbrowser.open(url)

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _shutdown_event.wait)

    if _server is not None:
        _server.should_exit = True

    # Asegurar que el resultado tenga todas las claves
    _result.setdefault("data", _data)
    _result.setdefault("products", _products_dicts)
    _result.setdefault("fotos", _captions)

    return _result


if __name__ == "__main__":
    from llm_client import extract_data
    from products.products import build_products, flatten_cotization, parse_price

    parser = argparse.ArgumentParser(description="UI de confirmación de datos extraídos.")
    parser.add_argument("file", help="Ruta al archivo (.docx, .pdf, …)")
    parser.add_argument("--provider", default="openrouter", choices=["gemini", "glm", "minimax", "openrouter"])
    parser.add_argument("--ocr", action="store_true")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    content = extract(args.file, ocr=args.ocr)
    data = extract_data(text=content.text, file_path=content.source, provider=args.provider)

    flat_config_path = flatten_cotization()
    price_flat = extract_data(
        text=content.text, file_path=content.source,
        provider=args.provider, data_path=flat_config_path,
        prompt_path="config/prompt_cotizacion.md",
    )
    Path(flat_config_path).unlink(missing_ok=True)
    products = build_products(parse_price(price_flat))

    from main import build_captions
    captions = build_captions(data, len(content.images))

    result = asyncio.run(main_async(content, data, products, captions, args.port))
    print("\nDatos confirmados:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
