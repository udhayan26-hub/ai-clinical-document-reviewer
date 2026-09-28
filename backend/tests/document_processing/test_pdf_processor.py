import io

import pytest
from PIL import Image

from app.core.enums import DocumentSourceType
from app.core.exceptions import CorruptedFileError, EmptyInputError, OCRFailedError
from app.document_processing.interfaces import ExtractionConfidence, OCRResult
from app.document_processing.pdf_processor import PDFProcessor
from tests.document_processing.fakes import FakeOCREngine
from tests.document_processing.fixture_paths import load_pdf_fixture


@pytest.fixture()
def processor() -> PDFProcessor:
    return PDFProcessor()


def test_valid_single_page_pdf(processor):
    result = processor.process(load_pdf_fixture("valid_text.pdf"))

    assert result.document_type == DocumentSourceType.PDF
    assert result.page_count == 1
    assert "Synthetic Clinical Note" in result.text
    assert "Chief complaint: headache and mild fatigue." in result.text
    assert result.confidence == ExtractionConfidence.HIGH
    assert result.requires_ocr is False
    assert result.warnings == []


def test_multi_page_pdf(processor):
    result = processor.process(load_pdf_fixture("multi_page.pdf"))

    assert result.page_count == 3
    for i in (1, 2, 3):
        assert f"Synthetic page {i} of 3." in result.text
    assert result.confidence == ExtractionConfidence.HIGH
    assert result.requires_ocr is False


def test_pdf_with_no_extractable_text_requires_ocr(processor):
    result = processor.process(load_pdf_fixture("no_text.pdf"))

    assert result.page_count == 1
    assert result.text == ""
    assert result.requires_ocr is True
    assert result.confidence is None
    assert any(w.code == "NO_EXTRACTABLE_TEXT" for w in result.warnings)


def test_pdf_with_some_pages_missing_text_still_extracts_available_text(processor):
    result = processor.process(load_pdf_fixture("mixed_pages.pdf"))

    assert result.page_count == 2
    assert "Synthetic page 1 has extractable text." in result.text
    assert result.requires_ocr is False
    assert result.confidence == ExtractionConfidence.MEDIUM
    assert any(w.code == "PAGE_HAS_NO_TEXT" for w in result.warnings)


def test_empty_pdf_raises_empty_input_error(processor):
    with pytest.raises(EmptyInputError):
        processor.process(load_pdf_fixture("empty.pdf"))


def test_corrupted_pdf_raises_corrupted_file_error(processor):
    with pytest.raises(CorruptedFileError):
        processor.process(load_pdf_fixture("corrupted.pdf"))


def test_empty_bytes_raises_empty_input_error(processor):
    with pytest.raises(EmptyInputError):
        processor.process(b"")


# ---- OCR fallback (PDFProcessor constructed with an ocr_engine) ----------


def test_native_text_pdf_does_not_invoke_ocr():
    """A page with usable native text must never be sent to OCR, even
    when an engine is configured."""
    engine = FakeOCREngine()
    processor = PDFProcessor(ocr_engine=engine)

    result = processor.process(load_pdf_fixture("valid_text.pdf"))

    assert engine.calls == []
    assert result.confidence == ExtractionConfidence.HIGH
    assert not any(w.code == "OCR_USED" for w in result.warnings)


def test_scanned_pdf_without_engine_flags_requires_ocr():
    """Same real-world scanned PDF as below, but with no engine configured
    — must degrade gracefully to the pre-OCR behavior, not crash."""
    result = PDFProcessor().process(load_pdf_fixture("scanned.pdf"))

    assert result.text == ""
    assert result.requires_ocr is True
    assert any(w.code == "NO_EXTRACTABLE_TEXT" for w in result.warnings)


def test_scanned_pdf_is_detected_and_ocrd():
    engine = FakeOCREngine(result=OCRResult(text="Synthetic scanned page content.", confidence=ExtractionConfidence.HIGH))
    processor = PDFProcessor(ocr_engine=engine)

    result = processor.process(load_pdf_fixture("scanned.pdf"))

    assert len(engine.calls) == 1  # the page's embedded image was sent for OCR
    assert result.text == "Synthetic scanned page content."
    assert result.requires_ocr is False
    assert result.confidence == ExtractionConfidence.HIGH
    assert any(w.code == "OCR_USED" for w in result.warnings)


def test_mixed_pdf_combines_native_and_ocr_text_preserving_page_order():
    engine = FakeOCREngine(
        result=OCRResult(text="Synthetic scanned page two content.", confidence=ExtractionConfidence.HIGH)
    )
    processor = PDFProcessor(ocr_engine=engine)

    result = processor.process(load_pdf_fixture("mixed_native_and_scanned.pdf"))

    assert len(engine.calls) == 1  # only page 2 (no native text) was sent to OCR
    assert "Synthetic native-text page one." in result.text
    assert "Synthetic scanned page two content." in result.text
    assert result.text.index("page one") < result.text.index("page two")  # order preserved
    assert any(w.code == "OCR_USED" for w in result.warnings)


def test_rotated_scanned_page_is_corrected_before_ocr():
    """page.rotation (a PDF /Rotate value) is a *display* instruction that
    pypdf's page.images does NOT apply to the raw embedded image bytes —
    verified empirically against real Tesseract (see docs/decisions/007-ocr.md
    "Limitations"): an uncorrected sideways scan OCR's as garbled/LOW
    confidence, and correcting by exactly `page.rotation` degrees (not the
    seemingly-more-intuitive negation) fixes it. This test only asserts the
    processor actually applies that correction (image dimensions swap for a
    90-degree-rotated page) — the *correctness* of the transform itself was
    validated once, manually, against the real engine, not per test run.
    """
    engine = FakeOCREngine(result=OCRResult(text="Synthetic rotated scan content.", confidence=ExtractionConfidence.HIGH))
    processor = PDFProcessor(ocr_engine=engine)

    processor.process(load_pdf_fixture("rotated_scanned.pdf"))

    assert len(engine.calls) == 1
    corrected_image = Image.open(io.BytesIO(engine.calls[0]))
    # The embedded raw image is 600x200; the page declares a 90-degree
    # rotation, so the corrected image handed to OCR must be 200x600, not
    # the raw, uncorrected 600x200.
    assert corrected_image.size == (200, 600)


def test_pdf_ocr_failure_becomes_warning_not_hard_failure():
    engine = FakeOCREngine(exception=OCRFailedError("OCR engine unavailable."))
    processor = PDFProcessor(ocr_engine=engine)

    result = processor.process(load_pdf_fixture("scanned.pdf"))  # does not raise

    assert result.text == ""
    assert result.requires_ocr is False  # OCR was attempted, not skipped
    assert any(w.code == "OCR_FAILED" for w in result.warnings)


def test_partial_ocr_failure_in_multi_page_document_does_not_appear_fully_reliable():
    """A document where page 1's OCR succeeds and page 2's fails must not
    read the same as a fully successful extraction: recovered text is
    still returned (page 1), but confidence must not be HIGH and the
    failure must be visible in warnings — a caller inspecting only the
    combined `text` field, without warnings/confidence, would otherwise
    wrongly conclude the whole document was reliably extracted."""
    engine = FakeOCREngine(
        results=[
            OCRResult(text="Page one recovered text.", confidence=ExtractionConfidence.HIGH),
            OCRFailedError("engine unavailable for this page"),
        ]
    )
    processor = PDFProcessor(ocr_engine=engine)

    result = processor.process(load_pdf_fixture("multi_page_scanned.pdf"))

    assert "Page one recovered text." in result.text
    assert result.confidence == ExtractionConfidence.MEDIUM  # not HIGH — one page still failed
    assert result.requires_ocr is False
    assert any(w.code == "OCR_USED" for w in result.warnings)
    assert any(w.code == "OCR_FAILED" for w in result.warnings)
