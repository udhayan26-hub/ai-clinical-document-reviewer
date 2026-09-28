import io

from PIL import Image

from app.core.enums import DocumentSourceType
from app.core.exceptions import CorruptedFileError, EmptyInputError
from app.document_processing.image_quality import assess_image_quality
from app.document_processing.interfaces import (
    DocumentProcessor,
    ExtractionWarning,
    NormalizedDocument,
    OCREngine,
)
from app.document_processing.normalization import normalize_whitespace


class ImageProcessor(DocumentProcessor):
    """OCRs standalone image submissions — scanned or handwritten
    documents submitted directly as an image (not embedded in a PDF).

    Does NOT own: which OCR engine is used (injected via `ocr_engine`;
    see `app.document_processing.interfaces.OCREngine`) or PDF-specific
    logic (see `pdf_processor.PDFProcessor`, which OCRs embedded page
    images through the same `OCREngine` interface — this class contains
    no PDF-specific code).

    Unlike `PDFProcessor`, there is no "native text" to fall back to:
    an OCR failure here has nothing to degrade to and propagates as
    `OCRFailedError` rather than becoming a warning.
    """

    def __init__(self, ocr_engine: OCREngine) -> None:
        self._ocr_engine = ocr_engine

    def process(self, raw_bytes: bytes) -> NormalizedDocument:
        if not raw_bytes:
            raise EmptyInputError("Submitted image is empty.")

        try:
            image = Image.open(io.BytesIO(raw_bytes))
            image.load()
        except Exception as exc:
            # Pillow raises different exception types (UnidentifiedImageError,
            # OSError, ValueError, ...) for unrecognized formats vs. truncated/
            # corrupt data — both mean the same thing to a caller: unreadable
            # image. Never let a Pillow exception itself propagate.
            raise CorruptedFileError(
                "The submitted image could not be read; it may be corrupted or in an unsupported format."
            ) from exc

        warnings: list[ExtractionWarning] = list(assess_image_quality(image))

        result = self._ocr_engine.recognize(raw_bytes)

        normalized_text = normalize_whitespace(result.text)
        warnings.extend(result.warnings)

        if normalized_text:
            warnings.append(
                ExtractionWarning(
                    code="OCR_USED",
                    message="Text was extracted via OCR; an image submission has no native text layer.",
                )
            )
        else:
            warnings.append(
                ExtractionWarning(code="PAGE_HAS_NO_TEXT", message="OCR did not detect any text in this image.")
            )

        return NormalizedDocument(
            document_type=DocumentSourceType.IMAGE,
            text=normalized_text,
            page_count=None,
            warnings=warnings,
            confidence=result.confidence,
            requires_ocr=False,
            metadata={"ocr_engine": type(self._ocr_engine).__name__},
        )
