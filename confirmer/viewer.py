"""
Helpers para convertir SourceContent a formatos mostrables en el browser.
"""
from __future__ import annotations

import base64
import io
from pathlib import Path

from processor.extractor import SourceContent


def get_viewer_type(content: SourceContent) -> str:
    """Determina cómo mostrar el documento en el browser."""
    if content.mime_type == "application/pdf":
        return "pdf"
    if "wordprocessingml" in content.mime_type:
        return "docx"
    return "text"


def docx_to_html(source: str) -> str:
    """Convierte .docx a HTML usando mammoth, retorna HTML completo."""
    import mammoth
    with open(source, "rb") as f:
        result = mammoth.convert_to_html(f, external_file_access=True)
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
  body {{ font-family: system-ui, sans-serif; padding: 2rem; line-height: 1.6; }}
  img {{ max-width: 100%; }}
  table {{ border-collapse: collapse; width: 100%; }}
  td, th {{ border: 1px solid #d1d5db; padding: 6px 10px; }}
</style></head>
<body>{result.value}</body></html>"""


def images_to_b64(content: SourceContent) -> list[str]:
    """Convierte las imágenes PIL a strings base64 PNG."""
    result = []
    for img in content.images:
        buf = io.BytesIO()
        thumb = img.copy()
        thumb.thumbnail((300, 300))
        thumb.save(buf, format="PNG")
        result.append(base64.b64encode(buf.getvalue()).decode())
    return result
