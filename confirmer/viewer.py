"""
Helpers para convertir SourceContent a formatos mostrables en el browser.
"""
from __future__ import annotations

import base64
import io

from processor.extractor import SourceContent


def get_viewer_type(content: SourceContent) -> str:
    """Determina cómo mostrar el documento en el browser."""
    if content.mime_type == "application/pdf":
        return "pdf"
    if "wordprocessingml" in content.mime_type:
        return "docx"
    return "text"


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
