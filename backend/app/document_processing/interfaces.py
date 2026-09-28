"""Document-processing contracts.

This module defines the `DocumentProcessor` abstraction and the
`NormalizedDocument` representation every concrete processor produces,
plus the `OCREngine` abstraction that `ImageProcessor` and `PDFProcessor`
depend on for scanned/image content. It must NOT depend on FastAPI,
SQLAlchemy, or any AI/ML (LLM) provider — it is pure document-handling,
called by the (not-yet-wired) services layer, never by API route
handlers directly.

Concrete processors (`text_processor.TextProcessor`,
`pdf_processor.PDFProcessor`, `image_processor.ImageProcessor`) all
implement this same interface so callers can treat any document type
uniformly: `processor.process(raw_bytes) -> NormalizedDocument`. See
`factory.get_processor` for source-type-based dispatch, and
`ocr_tesseract.py` for the one concrete `OCREngine` implementation —
`ImageProcessor`/`PDFProcessor` depend only on the `OCREngine` interface
below, never on `pytesseract` or any other OCR library directly, so the
engine can be swapped without touching either processor.
"""

from abc import ABC, abstractmethod
from enum import Enum

from pydantic import BaseModel, Field

from app.core.enums import DocumentSourceType


class ExtractionConfidence(str, Enum):
    """How much a caller should trust `NormalizedDocument.text` as a
    complete, accurate transcription of the source — not to be confused
    with `app.schemas.clinical_report.ConfidenceLevel`, which grades
    individual clinical findings, not raw text extraction.
    """

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ExtractionWarning(BaseModel):
    code: str
    message: str


class NormalizedDocument(BaseModel):
    """The single representation every `DocumentProcessor` produces,
    regardless of source type — the "normalized text" stage of the
    pipeline in docs/architecture/system-architecture.md §8.
    """

    document_type: DocumentSourceType
    text: str = Field(..., description="Normalized, extracted plain text. May be empty — see requires_ocr.")
    page_count: int | None = Field(default=None, description="Set for paginated sources (PDF); null for TEXT.")
    warnings: list[ExtractionWarning] = Field(default_factory=list)
    confidence: ExtractionConfidence | None = Field(
        default=None, description="Null when there is nothing to grade (e.g. empty result before OCR)."
    )
    requires_ocr: bool = Field(
        default=False,
        description="True when no extractable text layer was found and OCR is required to get any content. "
        "Never inferred as a failure — a clean 'no text here yet' result, not an error.",
    )
    metadata: dict[str, str] = Field(default_factory=dict, description="Small, processor-specific technical facts.")


class DocumentProcessor(ABC):
    """Turns raw document bytes of one specific source type into a
    `NormalizedDocument`.

    Does NOT own: clinical interpretation of the text (`app.ai`),
    persistence (`app.repositories`), or HTTP concerns (`app.api`).
    Implementations must never let a third-party library's exception
    (a parser error, a decode error, ...) escape `process()` — they must
    be caught and re-raised as one of the domain errors in
    `app.core.exceptions` so no Python stack trace ever reaches an API
    client.
    """

    @abstractmethod
    def process(self, raw_bytes: bytes) -> NormalizedDocument:
        """Raise `app.core.exceptions.EmptyInputError` for empty/blank
        input, `CorruptedFileError` if the bytes cannot be parsed as this
        processor's expected format, or a more specific subclass of
        `AppError` for other domain-specific failures.
        """
        raise NotImplementedError


class OCRResult(BaseModel):
    """Raw output of one `OCREngine.recognize()` call — one image in,
    one page/image's worth of text out. Deliberately smaller than
    `NormalizedDocument`: it has no `document_type` or `page_count`
    because a single OCR call doesn't know about the document it's part
    of — `ImageProcessor`/`PDFProcessor` fold this into a
    `NormalizedDocument` and add their own pipeline-level warnings
    (e.g. `OCR_USED`) on top of whatever `warnings` the engine itself
    reports (e.g. `OCR_LOW_CONFIDENCE`).
    """

    text: str = Field(default="", description="Recognized text; empty if nothing was detected.")
    confidence: ExtractionConfidence | None = Field(
        default=None, description="Null when no text was detected — nothing to grade."
    )
    warnings: list[ExtractionWarning] = Field(default_factory=list)


class OCREngine(ABC):
    """A pluggable OCR backend. `ImageProcessor` and `PDFProcessor` (for
    pages with no native text layer) depend on this interface only —
    never on a specific OCR library — so the engine can be replaced
    (a different local engine, or eventually a cloud OCR/vision service)
    without changing either processor or the `NormalizedDocument`
    contract they produce.
    """

    @abstractmethod
    def recognize(self, image_bytes: bytes) -> OCRResult:
        """Run OCR on a single image and return its text. Raise
        `app.core.exceptions.OCRFailedError` if recognition fails
        outright (the engine is unavailable, the image can't be decoded,
        etc.) — a merely empty/low-confidence result is not a failure
        and must be returned as a normal `OCRResult`, not raised.
        """
        raise NotImplementedError
