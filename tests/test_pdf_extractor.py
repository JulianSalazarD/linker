"""
Tests para PdfExtractor usando los archivos de pruebas/.
Ejecutar desde la raíz del proyecto:
    python -m unittest tests.test_pdf_extractor -v
"""
import unittest
from pathlib import Path

from processor.extractor import SourceContent, extract, get_extractor
from processor.pdf_extractor import PdfExtractor  # registra PdfExtractor

PRUEBAS = Path(__file__).parent.parent / "pruebas"
PDF_1 = PRUEBAS / "Bogotá Cra 62#64-10_260327_191939.pdf"
PDF_2 = PRUEBAS / "Transversal 56 # 104b-33_260331_172537 (1).pdf"


class TestPdfExtractorRegistro(unittest.TestCase):

    def test_get_extractor_devuelve_pdf(self):
        ext = get_extractor(PDF_1)
        self.assertIsInstance(ext, PdfExtractor)

    def test_can_handle_extension_pdf(self):
        ext = PdfExtractor()
        self.assertTrue(ext.can_handle("archivo.pdf"))
        self.assertTrue(ext.can_handle(Path("ruta/al/archivo.pdf")))

    def test_can_handle_no_soporta_otros(self):
        ext = PdfExtractor()
        self.assertFalse(ext.can_handle("archivo.docx"))
        self.assertFalse(ext.can_handle("archivo.txt"))


class TestPdfExtractorContenido(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.content_sin_ocr = extract(PDF_1)
        cls.content_con_ocr = extract(PDF_1, ocr=True)

    def test_retorna_source_content(self):
        self.assertIsInstance(self.content_sin_ocr, SourceContent)

    def test_sin_ocr_texto_vacio_en_pdf_escaneado(self):
        # Sin ocr=True los PDFs escaneados no producen texto
        self.assertEqual(self.content_sin_ocr.text, "")

    def test_con_ocr_texto_no_vacio(self):
        self.assertGreater(len(self.content_con_ocr.text), 0)

    def test_source_apunta_al_archivo(self):
        self.assertIn("Bogotá", self.content_sin_ocr.source)

    def test_mime_type_correcto(self):
        self.assertEqual(self.content_sin_ocr.mime_type, "application/pdf")

    def test_imagenes_encontradas(self):
        # PDF escaneado: las páginas se convierten en imágenes
        self.assertGreater(len(self.content_sin_ocr.images), 0)


class TestPdfExtractorMultiplesArchivos(unittest.TestCase):

    def test_todos_los_pdf_en_pruebas(self):
        archivos = list(PRUEBAS.glob("*.pdf"))
        self.assertGreater(len(archivos), 0, "No hay .pdf en pruebas/")
        for path in archivos:
            with self.subTest(archivo=path.name):
                content = extract(path)
                self.assertIsInstance(content, SourceContent)
                self.assertIsInstance(content.text, str)
                self.assertIsInstance(content.images, list)


if __name__ == "__main__":
    unittest.main(verbosity=2)
