import io

from PIL import Image
from pypdf import PdfReader

from app.core.enums import DocumentSourceType
from app.core.exceptions import CorruptedFileError, EmptyInputError, OCRFailedError
from app.document_processing.image_quality import assess_image_quality
from app.document_processing.interfaces import (
    DocumentProcessor,
    ExtractionConfidence,
    ExtractionWarning,
    NormalizedDocument,
    OCREngine,
)
from app.document_processing.normalization import normalize_whitespace


class PDFProcessor(DocumentProcessor):
    """Extracts text from PDFs, preferring each page's native text layer
    and falling back to OCR (via the injected `OCREngine`) only for pages
    that have none — never OCRs a page that already has usable native
    text. Page order is always preserved: native and OCR'd pages are
    combined in original page order, not grouped by source.

    `ocr_engine` is optional so this class works two ways:
    - `PDFProcessor()` (no engine) — native-text-only, matching the
      original (pre-OCR) behavior: a page with no native text is flagged
      via `requires_ocr`/`NO_EXTRACTABLE_TEXT`/`PAGE_HAS_NO_TEXT` warnings,
      never processed further. This is what every pre-existing test in
      `test_pdf_processor.py` exercises, unchanged.
    - `PDFProcessor(ocr_engine=...)` (what `factory.get_processor` wires
      up by default) — pages with no native text are OCR'd from their
      embedded page image before falling back to those same warnings.

    Does NOT own: OCR itself (delegated to `OCREngine`) or which engine
    is used.
    """

    def __init__(self, ocr_engine: OCREngine | None = None) -> None:
        self._ocr_engine = ocr_engine

    def process(self, raw_bytes: bytes) -> NormalizedDocument:
        if not raw_bytes:
            raise EmptyInputError("Submitted PDF file is empty.")

        try:
            reader = PdfReader(io.BytesIO(raw_bytes))
            page_count = len(reader.pages)
            native_page_texts = [page.extract_text() or "" for page in reader.pages]
        except Exception as exc:
            # pypdf can raise several different exception types (and some
            # non-pypdf ones, e.g. struct/ValueError) on malformed input —
            # all of them mean the same thing to a caller: unreadable PDF.
            raise CorruptedFileError(
                "The submitted PDF could not be read; it may be corrupted."
            ) from exc

        if page_count == 0:
            raise EmptyInputError("The submitted PDF contains no pages.")

        warnings: list[ExtractionWarning] = []
        final_pages: list[str] = []
        any_ocr_attempted = False

        for index, raw_page_text in enumerate(native_page_texts):
            page_number = index + 1
            native_text = normalize_whitespace(raw_page_text)
            if native_text:
                final_pages.append(native_text)
                continue

            if self._ocr_engine is None:
                final_pages.append("")
                continue

            any_ocr_attempted = True
            final_pages.append(self._ocr_page(reader.pages[index], page_number, warnings))

        pages_without_text = [i + 1 for i, t in enumerate(final_pages) if not t]
        combined_text = normalize_whitespace("\n\n".join(t for t in final_pages if t))

        if not combined_text:
            no_text_message = (
                "No text could be extracted from any page, including via OCR."
                if any_ocr_attempted
                else "No extractable text was found on any page; OCR is required."
            )
            warnings.append(ExtractionWarning(code="NO_EXTRACTABLE_TEXT", message=no_text_message))
            return NormalizedDocument(
                document_type=DocumentSourceType.PDF,
                text="",
                page_count=page_count,
                warnings=warnings,
                confidence=None,
                requires_ocr=self._ocr_engine is None,
                metadata={"pages_with_text": "0", "pages_without_text": str(page_count)},
            )

        for page_number in pages_without_text:
            warnings.append(
                ExtractionWarning(
                    code="PAGE_HAS_NO_TEXT",
                    message=f"Page {page_number} contains no extractable text"
                    + (" even after OCR" if any_ocr_attempted else "; it may require OCR")
                    + ".",
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

    def _ocr_page(self, page, page_number: int, warnings: list[ExtractionWarning]) -> str:
        """OCR every image embedded in one page (typically one full-page
        scan) and return its combined, normalized text — or "" (with a
        warning recorded into `warnings`) if there's nothing to OCR or
        OCR fails. Never raises: a single page's OCR failure must not
        abort the rest of a multi-page document (contrast `ImageProcessor`,
        where OCR failure has no page-level fallback and propagates).
        """
        try:
            image_byte_list = [image_file.data for image_file in page.images]
        except Exception:
            warnings.append(
                ExtractionWarning(
                    code="OCR_FAILED",
                    message=f"Page {page_number}: could not read embedded image data for OCR.",
                )
            )
            return ""

        if not image_byte_list:
            return ""

        # PDF pages can carry a /Rotate value (always a multiple of 90) that
        # tells a *viewer* how to display the page — pypdf's page.images
        # returns the image's raw stored bytes and does NOT apply this
        # rotation (verified empirically: a genuinely sideways-scanned page
        # OCR'd garbled without correction, and cleanly at HIGH confidence
        # once rotated by exactly `page.rotation` degrees — not the
        # seemingly-more-intuitive negated value). Pages with no /Rotate
        # (rotation == 0, the common case) are unaffected by this at all.
        rotation = page.rotation % 360

        recognized_parts: list[str] = []
        page_warnings: list[ExtractionWarning] = []
        ocr_failed = False

        for image_bytes in image_byte_list:
            ocr_input_bytes = image_bytes
            try:
                pil_image = Image.open(io.BytesIO(image_bytes))
                if rotation:
                    pil_image = pil_image.rotate(rotation, expand=True)
                    buf = io.BytesIO()
                    pil_image.save(buf, format="PNG")
                    ocr_input_bytes = buf.getvalue()
                page_warnings.extend(assess_image_quality(pil_image))
            except Exception:
                pass  # best-effort: if we can't decode for rotation/quality checks here,
                # still let the OCR engine attempt its own decode below, on the original bytes

            try:
                result = self._ocr_engine.recognize(ocr_input_bytes)
            except OCRFailedError as exc:
                ocr_failed = True
                page_warnings.append(
                    ExtractionWarning(code="OCR_FAILED", message=f"Page {page_number}: {exc.message}")
                )
                continue

            if result.text.strip():
                recognized_parts.append(result.text)
            page_warnings.extend(result.warnings)

        page_text = normalize_whitespace("\n\n".join(recognized_parts))

        if page_text:
            warnings.append(
                ExtractionWarning(
                    code="OCR_USED",
                    message=f"Page {page_number} had no native text layer; text was extracted via OCR.",
                )
            )
            warnings.extend(w for w in page_warnings if w not in warnings)
        elif ocr_failed:
            warnings.extend(w for w in page_warnings if w not in warnings)
        # else: page had image(s) but OCR cleanly found no text — handled by
        # the caller's PAGE_HAS_NO_TEXT/NO_EXTRACTABLE_TEXT warnings.

        return page_text
