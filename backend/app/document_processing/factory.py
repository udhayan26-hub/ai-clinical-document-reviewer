from collections.abc import Callable

from app.core.enums import DocumentSourceType
from app.core.exceptions import UnsupportedFileTypeError
from app.document_processing.image_processor import ImageProcessor
from app.document_processing.interfaces import DocumentProcessor
from app.document_processing.ocr_tesseract import get_default_ocr_engine
from app.document_processing.pdf_processor import PDFProcessor
from app.document_processing.text_processor import TextProcessor

# Factories rather than plain classes so PDF/IMAGE can be wired with the
# app's default OCREngine while TEXT needs no such dependency — dispatch
# stays a single, deterministic dict lookup either way.
_PROCESSOR_FACTORIES: dict[DocumentSourceType, Callable[[], DocumentProcessor]] = {
    DocumentSourceType.TEXT: lambda: TextProcessor(),
    DocumentSourceType.PDF: lambda: PDFProcessor(ocr_engine=get_default_ocr_engine()),
    DocumentSourceType.IMAGE: lambda: ImageProcessor(ocr_engine=get_default_ocr_engine()),
}


def get_processor(source_type: DocumentSourceType) -> DocumentProcessor:
    """Return the `DocumentProcessor` for a given source type, wired with
    the app's configured default `OCREngine` (`Settings.ocr_engine`) for
    PDF/IMAGE. Selecting an IMAGE processor always succeeds — whether
    *processing* succeeds depends on the image and the OCR engine.

    Tests that want deterministic, offline behavior should construct
    `PDFProcessor`/`ImageProcessor` directly with a fake `OCREngine`
    (see `tests/document_processing/fakes.py`) rather than going through
    this factory, since its default engine talks to a real, possibly-
    not-installed OCR binary.
    """
    factory_fn = _PROCESSOR_FACTORIES.get(source_type)
    if factory_fn is None:
        raise UnsupportedFileTypeError(f"No document processor is registered for '{source_type}'.")
    return factory_fn()
