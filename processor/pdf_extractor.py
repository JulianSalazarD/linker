"""
Extractor para archivos .pdf.

Estrategia:
  1. pdfplumber extrae texto nativo.
  2. Si la página no tiene texto (PDF escaneado), aplica OCR con tesseract.
  3. Detecta y extrae fotos embebidas dentro de páginas-imagen (ej. PDFs exportados desde hojas de cálculo).
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from processor.extractor import BaseExtractor, SourceContent, register_extractor
from processor.ocr import ocr_image

_MIN_PHOTO_PX = 100  # mínimo ancho/alto en píxeles para considerar una región como foto


def _extract_photos_from_page(
    pil_img: Image.Image,
    *,
    brightness_threshold: int = 200,
    sat_threshold: int = 25,
    min_size: int = _MIN_PHOTO_PX,
) -> list[Image.Image]:
    """Detecta y recorta fotos individuales dentro de una imagen de página.

    Usa perfil de brillo (separar bandas verticales) + saturación de color
    (delimitar bordes horizontales) para aislar fotos del fondo de grid.
    """
    img = np.array(pil_img)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
    sat = hsv[:, :, 1]

    h, w = gray.shape

    # Columnas con contenido saturado (donde están las fotos)
    sat_col_sum = np.sum(sat > sat_threshold, axis=0)
    photo_cols = np.where(sat_col_sum > h * 0.05)[0]
    if len(photo_cols) == 0:
        return []
    x_start, x_end = int(photo_cols[0]), int(photo_cols[-1])

    # Perfil de brillo promedio por fila en la zona de fotos
    region = gray[:, x_start:x_end]
    row_avg = np.mean(region, axis=1)

    # Filas de foto: brillo bajo. Filas de grid/vacío: brillo alto.
    is_photo_row = row_avg < brightness_threshold

    # Encontrar rangos contiguos de filas de foto
    bands: list[tuple[int, int]] = []
    in_band = False
    start = 0
    for y in range(len(is_photo_row)):
        if is_photo_row[y]:
            if not in_band:
                start = y
                in_band = True
        else:
            if in_band:
                bands.append((start, y))
                in_band = False
    if in_band:
        bands.append((start, len(is_photo_row)))

    # Recortar cada banda refinando los límites x con saturación
    photos: list[Image.Image] = []
    for y1, y2 in bands:
        if (y2 - y1) < min_size:
            continue
        band_sat = sat[y1:y2, :]
        col_sum = np.sum(band_sat > sat_threshold, axis=0)
        col_threshold = (y2 - y1) * 0.05
        active_cols = np.where(col_sum > col_threshold)[0]
        if len(active_cols) == 0:
            continue
        bx1, bx2 = int(active_cols[0]), int(active_cols[-1])
        if (bx2 - bx1) < min_size:
            continue
        photos.append(pil_img.crop((bx1, y1, bx2, y2)))

    return photos


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

                # Página escaneada: OCR para extraer texto
                if not text.strip():
                    pil_img = page.to_image(resolution=200).original
                    ocr_text = ocr_image(pil_img)
                    if ocr_text.strip():
                        pages_text.append(ocr_text)

                # Renderizar página y extraer fotos embebidas
                pil_img = page.to_image(resolution=200).original
                page_photos = _extract_photos_from_page(pil_img)

                if page_photos:
                    images.extend(page_photos)
                elif not text.strip():
                    # Sin texto ni fotos detectadas: guardar página completa
                    images.append(pil_img)

        return SourceContent(
            text="\n".join(t for t in pages_text if t.strip()),
            images=images,
            source=str(source),
            mime_type="application/pdf",
        )


register_extractor(PdfExtractor())

