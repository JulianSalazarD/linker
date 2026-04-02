for _mod in ["processor.docx_extractor", "processor.pdf_extractor"]:
    __import__(_mod)

from processor.extractor import extract, get_extractor, register_extractor

__all__ = ["extract", "get_extractor", "register_extractor"]
