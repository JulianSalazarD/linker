"""
OCR sobre imágenes PIL usando pytesseract.

Requiere tesseract instalado en el sistema:
  - Linux:   sudo apt install tesseract-ocr tesseract-ocr-spa
             o:  sudo pacman -S tesseract tesseract-data-spa
  - macOS:   brew install tesseract tesseract-lang
  - Windows: descargar instalador desde https://github.com/UB-Mannheim/tesseract/wiki
             y agregar al PATH (o configurar pytesseract.pytesseract.tesseract_cmd)
"""
from __future__ import annotations

from PIL import Image
import pytesseract


def ocr_image(img: Image.Image) -> str:
    """Extrae texto de una imagen PIL usando Tesseract."""
    return pytesseract.image_to_string(img, lang="spa+eng")
