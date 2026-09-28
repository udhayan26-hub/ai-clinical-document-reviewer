import io

from pypdf import PdfReader

from app.core.enums import DocumentSourceType
from app.core.exceptions import CorruptedFileError, EmptyInputError
from app.document_processing.interfaces import (
    DocumentProcessor,
    ExtractionConfidence,
    ExtractionWarning,
    NormalizedDocument,
)
from app.document_processing.normalization import normalize_whitespace


class PDFProcessor(DocumentProcessor):
    """Extracts text from PDFs that carry a native text layer (typed
    PDFs). Does NOT perform OCR: a page with no extractable text is not
    an error — it is reported via `NormalizedDocument.requires_ocr` and a
    warning, never silently dropped or faked. Routing a document that
    needs OCR to an actual OCR engine is a future concern for whatever
    orchestrates processors (not yet implemented) — this processor's job
    ends at "here is what could be extracted without one."
    """

    def process(self, raw_bytes: bytes) -> NormalizedDocument:
        if not raw_bytes:
            raise EmptyInputError("Submitted PDF file is empty.")

        try:
            reader = PdfReader(io.BytesIO(raw_bytes))
            page_count = len(reader.pages)
            page_texts = [page.extract_text() or "" for page in reader.pages]
        except Exception as exc:
            # pypdf can raise several different exception types (and some
            # non-pypdf ones, e.g. struct/ValueError) on malformed input —
            # all of them mean the same thing to a caller: unreadable PDF.
            raise CorruptedFileError(
                "The submitted PDF could not be read; it may be corrupted."
            ) from exc

        if page_count == 0:
            raise EmptyInputError("The submitted PDF contains no pages.")

        normalized_pages = [normalize_whitespace(t) for t in page_texts]
        pages_without_text = [i + 1 for i, t in enumerate(normalized_pages) if not t]
        combined_text = normalize_whitespace("\n\n".join(t for t in normalized_pages if t))

        warnings: list[ExtractionWarning] = []

        if not combined_text:
            warnings.append(
                ExtractionWarning(
                    code="NO_EXTRACTABLE_TEXT",
                    message="No extractable text was found on any page; OCR is required.",
                )
            )
            return NormalizedDocument(
                document_type=DocumentSourceType.PDF,
                text="",
                page_count=page_count,
                warnings=warnings,
                confidence=None,
                requires_ocr=True,
                metadata={"pages_with_text": "0", "pages_without_text": str(page_count)},
            )

        for page_number in pages_without_text:
            warnings.append(
                ExtractionWarning(
                    code="PAGE_HAS_NO_TEXT",
                    message=f"Page {page_number} contains no extractable text; it may require OCR.",
                )
            )

        confidence = ExtractionConfidence.MEDIUM if pages_without_text else ExtractionConfidence.HIGH

        return NormalizedDocument(
            document_type=DocumentSourceType.PDF,
            text=combined_text,
            page_count=page_count,
            warnings=warnings,
            confidence=confidence,
            requires_ocr=False,
            metadata={
                "pages_with_text": str(page_count - len(pages_without_text)),
                "pages_without_text": str(len(pages_without_text)),
            },
        )
