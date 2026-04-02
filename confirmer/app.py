"""
UI de confirmación de datos extraídos.

Uso:
    python confirmer/app.py <archivo> [--provider minimax] [--ocr] [--port 8000]
"""
from __future__ import annotations

import argparse
import asyncio
import os
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
from llm_client import extract_data
from confirmer.viewer import docx_to_html, get_viewer_type, images_to_b64

# ---------------------------------------------------------------------------
# Estado global de la sesión (una sesión a la vez)
# ---------------------------------------------------------------------------

_content: SourceContent | None = None
_data: dict = {}
_result: dict | None = None
_shutdown_event = threading.Event()  # threading.Event es seguro entre loops/hilos

# ---------------------------------------------------------------------------
# App FastAPI
# ---------------------------------------------------------------------------

_here = Path(__file__).parent

app = FastAPI()
app.mount("/static", StaticFiles(directory=str(_here / "static")), name="static")

_jinja_env = Environment(loader=FileSystemLoader(str(_here / "templates")), autoescape=True)
_jinja_env.filters["basename"] = lambda p: Path(p).name


@app.get("/")
async def index():
    assert _content is not None
    html = _jinja_env.get_template("index.html").render(
        viewer_type=get_viewer_type(_content),
        text=_content.text,
        source=_content.source,
        fields=_data,
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
    return JSONResponse({"images": images_to_b64(_content)})


_server: uvicorn.Server | None = None


@app.post("/confirm")
async def confirm(request: Request):
    global _result
    body = await request.json()
    _result = body.get("fields", {})
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


async def main_async(file_path: str, provider: str, ocr: bool, port: int) -> dict:
    global _content, _data

    _shutdown_event.clear()
    print(f"Extrayendo: {file_path}")
    _content = extract(file_path, ocr=ocr)
    print(f"  texto={len(_content.text)} chars  imgs={len(_content.images)}")

    print(f"Infiriendo campos con {provider}…")
    _data = extract_data(text=_content.text, file_path=_content.source, provider=provider)

    t = threading.Thread(target=run_server, args=(port,), daemon=True)
    t.start()

    url = f"http://127.0.0.1:{port}"
    print(f"Abriendo {url}")
    webbrowser.open(url)

    # Esperar en executor para no bloquear el loop con threading.Event.wait()
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _shutdown_event.wait)

    # Detener uvicorn limpiamente
    if _server is not None:
        _server.should_exit = True

    return _result or _data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UI de confirmación de datos extraídos.")
    parser.add_argument("file", help="Ruta al archivo (.docx, .pdf, …)")
    parser.add_argument("--provider", default="minimax", choices=["gemini", "glm", "minimax"])
    parser.add_argument("--ocr", action="store_true")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    import json
    result = asyncio.run(main_async(args.file, args.provider, args.ocr, args.port))
    print("\nDatos confirmados:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
