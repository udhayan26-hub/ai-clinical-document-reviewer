from app.core.exceptions import OCRNotImplementedError
from app.document_processing.interfaces import DocumentProcessor, NormalizedDocument


class ImageProcessor(DocumentProcessor):
    """Stub only. Scanned/handwritten image processing requires OCR,
    which is a later phase (see docs/decisions/004-ai-ml.md). This class
    exists now so `factory.get_processor` can already dispatch
    `DocumentSourceType.IMAGE` to *something* implementing the shared
    `DocumentProcessor` interface, rather than the caller needing a
    special case for "not built yet".

    When OCR is implemented, this class gets a real `process()` body
    that runs an `OCRProcessor`-style engine and returns a
    `NormalizedDocument` exactly like `TextProcessor`/`PDFProcessor` do
    today — no interface change, no caller changes required.
    """

    def process(self, raw_bytes: bytes) -> NormalizedDocument:
        raise OCRNotImplementedError(
            "Image processing requires OCR, which is not implemented yet."
        )
