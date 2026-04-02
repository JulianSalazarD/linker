"""
Extractor para archivos .pdf.

Estrategia:
  1. pdfplumber extrae texto nativo.
  2. Si la página no tiene texto (PDF escaneado) y ocr=True, renderiza la página y aplica OCR.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from processor.extractor import BaseExtractor, SourceContent, register_extractor
from processor.ocr import ocr_image


class PdfExtractor(BaseExtractor):
    supported = (".pdf",)

    def extract(self, source: str | Path, *, ocr: bool = False) -> SourceContent:
        import pdfplumber

        pages_text: list[str] = []
        images: list[Image.Image] = []

        with pdfplumber.open(str(source)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                if text.strip():
                    pages_text.append(text)
                else:
                    pil_img = page.to_image(resolution=200).original
                    images.append(pil_img)
                    if ocr:
                        pages_text.append(ocr_image(pil_img))

        return SourceContent(
            text="\n".join(t for t in pages_text if t.strip()),
            images=images,
            source=str(source),
            mime_type="application/pdf",
        )


register_extractor(PdfExtractor())

