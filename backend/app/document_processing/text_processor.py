from app.core.enums import DocumentSourceType
from app.core.exceptions import CorruptedFileError, EmptyInputError
from app.document_processing.interfaces import (
    DocumentProcessor,
    ExtractionConfidence,
    NormalizedDocument,
)
from app.document_processing.normalization import normalize_whitespace


class TextProcessor(DocumentProcessor):
    """Handles plain-text submissions. No extraction is needed — the
    submitted bytes already *are* the document; this processor's only
    job is decoding and normalization.
    """

    def process(self, raw_bytes: bytes) -> NormalizedDocument:
        try:
            raw_text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CorruptedFileError(
                "Submitted text could not be decoded as UTF-8."
            ) from exc

        normalized = normalize_whitespace(raw_text)
        if not normalized:
            raise EmptyInputError("Submitted text is empty or contains only whitespace.")

        return NormalizedDocument(
            document_type=DocumentSourceType.TEXT,
            text=normalized,
            page_count=None,
            confidence=ExtractionConfidence.HIGH,
        )
