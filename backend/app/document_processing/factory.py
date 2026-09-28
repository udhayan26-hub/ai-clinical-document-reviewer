from app.core.enums import DocumentSourceType
from app.core.exceptions import UnsupportedFileTypeError
from app.document_processing.image_processor import ImageProcessor
from app.document_processing.interfaces import DocumentProcessor
from app.document_processing.pdf_processor import PDFProcessor
from app.document_processing.text_processor import TextProcessor

_PROCESSORS: dict[DocumentSourceType, type[DocumentProcessor]] = {
    DocumentSourceType.TEXT: TextProcessor,
    DocumentSourceType.PDF: PDFProcessor,
    DocumentSourceType.IMAGE: ImageProcessor,
}


def get_processor(source_type: DocumentSourceType) -> DocumentProcessor:
    """Return the `DocumentProcessor` for a given source type. Selecting
    an IMAGE processor succeeds (it exists) — whether *processing*
    succeeds is a separate concern (`ImageProcessor.process` currently
    always raises `OCRNotImplementedError`; see its docstring).
    """
    processor_cls = _PROCESSORS.get(source_type)
    if processor_cls is None:
        raise UnsupportedFileTypeError(f"No document processor is registered for '{source_type}'.")
    return processor_cls()
