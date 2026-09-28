"""Document-processing contracts.

This module defines the `DocumentProcessor` abstraction and the
`NormalizedDocument` representation every concrete processor produces.
It must NOT depend on FastAPI, SQLAlchemy, or any AI/ML provider — it is
pure document-handling, called by the (not-yet-wired) services layer,
never by API route handlers directly.

Concrete processors (`text_processor.TextProcessor`,
`pdf_processor.PDFProcessor`, `image_processor.ImageProcessor`) all
implement this same interface so callers can treat any document type
uniformly: `processor.process(raw_bytes) -> NormalizedDocument`. See
`factory.get_processor` for source-type-based dispatch.
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
