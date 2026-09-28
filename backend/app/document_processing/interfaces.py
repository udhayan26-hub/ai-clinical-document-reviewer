"""Document-processing contracts.

This module defines *interfaces only* — no OCR engine, PDF library, or
text-extraction implementation lives here yet. Concrete implementations
(e.g. a Tesseract-backed OCRProcessor, a pypdf-backed DocumentTextExtractor)
will be added later behind these same interfaces, selected by
`app.document_processing.factory` (not yet implemented) based on
`DocumentSourceType`, so `app.services.analysis_service` never depends on
a specific library.

This module must NOT depend on FastAPI, SQLAlchemy, or any AI/ML
provider — it is pure document-handling and is called by the services
layer, never by API route handlers directly.
"""

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class ExtractionWarning(BaseModel):
    code: str
    message: str


class ExtractionResult(BaseModel):
    """Normalized output of any text-extraction or OCR step."""

    text: str = Field(..., description="Normalized plain text extracted from the source.")
    warnings: list[ExtractionWarning] = Field(default_factory=list)
    page_count: int | None = Field(default=None, description="Set for paginated sources (PDF).")


class DocumentTextExtractor(ABC):
    """Extracts text from documents that carry a native text layer:
    plain-text submissions and typed (non-scanned) PDFs.

    Does NOT own: OCR of scanned/handwritten content (see `OCRProcessor`),
    clinical interpretation of the text (see `app.ai.interfaces`), or
    persistence of the result (see `app.repositories`).
    """

    @abstractmethod
    def supports(self, content_type: str) -> bool:
        """Whether this extractor can handle the given MIME type."""
        raise NotImplementedError

    @abstractmethod
    def extract(self, raw_bytes: bytes, content_type: str) -> ExtractionResult:
        """Extract normalized text. Must raise
        `app.core.exceptions.CorruptedFileError` if the bytes cannot be
        parsed as the declared content type, and
        `app.core.exceptions.TextExtractionError` for any other
        extraction failure.
        """
        raise NotImplementedError


class OCRProcessor(ABC):
    """Extracts text from image-based content: scanned pages and
    handwritten documents, whether submitted directly as an image or
    embedded in a PDF page with no text layer.

    Does NOT own: typed-text extraction (see `DocumentTextExtractor`),
    clinical interpretation, or the decision of *when* OCR is needed
    (that routing lives in `app.document_processing.factory`, not yet
    implemented).
    """

    @abstractmethod
    def supports(self, content_type: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def extract(self, image_bytes: bytes, content_type: str) -> ExtractionResult:
        """Run OCR and return normalized text. Must raise
        `app.core.exceptions.OCRFailedError` when recognition fails
        outright (not merely low-confidence — low confidence should be
        surfaced via `ExtractionResult.warnings`).
        """
        raise NotImplementedError
