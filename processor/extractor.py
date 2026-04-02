"""
Interfaz base para extracción de texto e imágenes desde documentos.

Las implementaciones concretas se registran con `register_extractor`
o colocando extractores en módulos separados que llamen a dicha función.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image


@dataclass
class SourceContent:
    """Resultado normalizado de cualquier extractor."""
    text: str
    images: list[Image.Image] = field(default_factory=list)
    source: str = ""
    mime_type: str = ""


class BaseExtractor(ABC):
    """Interfaz común para todos los extractores."""

    #: extensiones o patrones que maneja este extractor (en minúsculas)
    supported: tuple[str, ...] = ()

    @abstractmethod
    def extract(self, source: str | Path, *, ocr: bool = False) -> SourceContent:
        """Lee la fuente y retorna un SourceContent."""

    def can_handle(self, source: str | Path) -> bool:
        """Devuelve True si este extractor puede manejar la fuente dada."""
        s = str(source).lower()
        return any(s.endswith(ext) or ext in s for ext in self.supported)


# ---------------------------------------------------------------------------
# Registro
# ---------------------------------------------------------------------------

_EXTRACTORS: list[BaseExtractor] = []


def register_extractor(extractor: BaseExtractor) -> None:
    """Registra un extractor. Los últimos registrados tienen mayor prioridad."""
    _EXTRACTORS.insert(0, extractor)


def get_extractor(source: str | Path) -> BaseExtractor:
    """Devuelve el primer extractor que pueda manejar la fuente."""
    for ext in _EXTRACTORS:
        if ext.can_handle(source):
            return ext
    raise ValueError(
        f"No hay extractor registrado para: {source!r}\n"
        f"Registrados: {[type(e).__name__ for e in _EXTRACTORS]}"
    )


def extract(source: str | Path, *, ocr: bool = False) -> SourceContent:
    """Detecta el extractor adecuado y retorna el contenido."""
    return get_extractor(source).extract(source, ocr=ocr)


if __name__ == "__main__":
    import sys

    # Asegurar que la raíz del proyecto esté en sys.path
    _root = str(Path(__file__).parent.parent)
    if _root not in sys.path:
        sys.path.insert(0, _root)

    # Importar extractores concretos — se registran en processor.extractor,
    # no en __main__, por eso usamos processor.extractor.extract() a continuación
    for _mod in ["processor.docx_extractor"]:
        __import__(_mod)
    from processor.extractor import extract as _extract

    if len(sys.argv) < 2:
        print("Uso: python processor/extractor.py <archivo>")
        sys.exit(1)

    _path = Path(sys.argv[1])
    _content = _extract(_path)
    print(f"Texto extraído de {_path}:")
    print(_content.text[:500] + "...")
    print(f"Imágenes encontradas: {len(_content.images)}")