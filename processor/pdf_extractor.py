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


if __name__ == "__main__":
    import sys

    _root = str(Path(__file__).parent.parent)
    if _root not in sys.path:
        sys.path.insert(0, _root)

    from processor.extractor import extract as _extract

    if len(sys.argv) < 2:
        print("Uso: python processor/pdf_extractor.py <archivo.pdf> [--ocr]")
        sys.exit(1)

    _path = Path(sys.argv[1])
    _ocr = "--ocr" in sys.argv
    _content = _extract(_path, ocr=_ocr)
    print(f"Texto extraído de {_path} (ocr={_ocr}):")
    print(_content.text[:500] + ("..." if len(_content.text) > 500 else ""))
    print(f"Imágenes encontradas: {len(_content.images)}")
