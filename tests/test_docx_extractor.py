"""
Tests para DocxExtractor usando los archivos de pruebas/.
Ejecutar desde la raíz del proyecto:
    python -m unittest tests.test_docx_extractor -v
"""
import unittest
from pathlib import Path

from processor.extractor import SourceContent, extract, get_extractor
from processor.docx_extractor import DocxExtractor  # registra DocxExtractor al importar

PRUEBAS = Path(__file__).parent.parent / "pruebas"
DOCX_SIMPLE = PRUEBAS / "carera 26 No 50 - 47_260318_200729.docx"
DOCX_EXTRA  = PRUEBAS / "Calle 182 # 45 45_260318_201415.docx"


class TestDocxExtractorRegistro(unittest.TestCase):

    def test_get_extractor_devuelve_docx(self):
        ext = get_extractor(DOCX_SIMPLE)
        self.assertIsInstance(ext, DocxExtractor)

    def test_can_handle_extension_docx(self):
        ext = DocxExtractor()
        self.assertTrue(ext.can_handle("archivo.docx"))
        self.assertTrue(ext.can_handle(Path("ruta/al/archivo.docx")))

    def test_can_handle_no_soporta_otros(self):
        ext = DocxExtractor()
        self.assertFalse(ext.can_handle("archivo.pdf"))
        self.assertFalse(ext.can_handle("archivo.txt"))


class TestDocxExtractorContenido(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.content = extract(DOCX_SIMPLE)

    def test_retorna_source_content(self):
        self.assertIsInstance(self.content, SourceContent)

    def test_texto_no_vacio(self):
        self.assertGreater(len(self.content.text), 0)

    def test_source_apunta_al_archivo(self):
        self.assertIn("carera 26", self.content.source)

    def test_mime_type_correcto(self):
        self.assertEqual(
            self.content.mime_type,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    def test_imagenes_encontradas(self):
        self.assertGreater(len(self.content.images), 0)

    def test_texto_contiene_datos_conocidos(self):
        # El archivo tiene "Andrea Ladino" y la dirección
        self.assertIn("Andrea Ladino", self.content.text)
        self.assertIn("21 metros", self.content.text)


class TestDocxExtractorMultiplesArchivos(unittest.TestCase):

    def test_todos_los_docx_en_pruebas(self):
        archivos = list(PRUEBAS.glob("*.docx"))
        self.assertGreater(len(archivos), 0, "No hay .docx en pruebas/")
        for path in archivos:
            with self.subTest(archivo=path.name):
                content = extract(path)
                self.assertIsInstance(content, SourceContent)
                self.assertIsInstance(content.text, str)
                self.assertIsInstance(content.images, list)

    def test_archivo_extra(self):
        content = extract(DOCX_EXTRA)
        self.assertGreater(len(content.text), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
