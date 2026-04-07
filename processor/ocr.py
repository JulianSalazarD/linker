"""
OCR sobre imágenes PIL.

Prioridad:
  1. pytesseract  (requiere tesseract instalado en el sistema)
  2. easyocr      (fallback, solo Python)
"""
from __future__ import annotations

from PIL import Image

# Reader de easyocr memoizado para no reinicializarlo en cada llamada
_easyocr_reader = None


def _read_easyocr(img: Image.Image) -> str:
    global _easyocr_reader
    import numpy as np
    import easyocr

    if _easyocr_reader is None:
        _easyocr_reader = easyocr.Reader(["es", "en"], gpu=False)
    results = _easyocr_reader.readtext(np.array(img.convert("RGB")), detail=0, paragraph=True)
    return "\n".join(str(result) for result in results)


def _read_pytesseract(img: Image.Image) -> str:
    import pytesseract
    return pytesseract.image_to_string(img, lang="spa+eng")


def ocr_image(img: Image.Image) -> str:
    """Extrae texto de una imagen PIL. Usa pytesseract si está disponible, si no easyocr."""
    try:
        return _read_pytesseract(img)
    except ImportError:
        # pytesseract no instalado como paquete
        return _read_easyocr(img)
    except Exception as e:
        # Captura TesseractNotFoundError (binario no en PATH) sin importar el módulo
        if "TesseractNotFound" in type(e).__name__ or "tesseract" in str(e).lower():
            return _read_easyocr(img)
        raise
