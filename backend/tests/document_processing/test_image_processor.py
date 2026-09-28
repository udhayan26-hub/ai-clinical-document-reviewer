import pytest

from app.core.enums import DocumentSourceType
from app.core.exceptions import CorruptedFileError, EmptyInputError, OCRFailedError
from app.document_processing.image_processor import ImageProcessor
from app.document_processing.interfaces import (
    ExtractionConfidence,
    ExtractionWarning,
    OCRResult,
)
from tests.document_processing.fakes import FakeOCREngine
from tests.document_processing.fixture_paths import load_image_fixture


def test_valid_image_uses_ocr_abstraction_and_returns_normalized_document():
    engine = FakeOCREngine(result=OCRResult(text="Synthetic printed clinical note.", confidence=ExtractionConfidence.HIGH))
    processor = ImageProcessor(ocr_engine=engine)
    raw_bytes = load_image_fixture("clear_printed.png")

    result = processor.process(raw_bytes)

    assert engine.calls == [raw_bytes]  # ImageProcessor delegates to the injected engine
    assert result.document_type == DocumentSourceType.IMAGE
    assert result.text == "Synthetic printed clinical note."
    assert result.page_count is None
    assert result.confidence == ExtractionConfidence.HIGH
    assert result.requires_ocr is False
    assert any(w.code == "OCR_USED" for w in result.warnings)


def test_low_quality_image_gets_quality_warning():
    engine = FakeOCREngine(result=OCRResult(text="hi", confidence=ExtractionConfidence.MEDIUM))
    processor = ImageProcessor(ocr_engine=engine)

    result = processor.process(load_image_fixture("low_quality.png"))

    assert any(w.code == "IMAGE_QUALITY_LOW" for w in result.warnings)


def test_engine_warnings_are_preserved():
    engine = FakeOCREngine(
        result=OCRResult(
            text="some text",
            confidence=ExtractionConfidence.LOW,
            warnings=[ExtractionWarning(code="OCR_LOW_CONFIDENCE", message="low confidence")],
        )
    )
    processor = ImageProcessor(ocr_engine=engine)

    result = processor.process(load_image_fixture("clear_printed.png"))

    assert result.confidence == ExtractionConfidence.LOW
    assert any(w.code == "OCR_LOW_CONFIDENCE" for w in result.warnings)


def test_no_text_recognized_returns_page_has_no_text_warning():
    engine = FakeOCREngine(result=OCRResult(text="", confidence=None))
    processor = ImageProcessor(ocr_engine=engine)

    result = processor.process(load_image_fixture("clear_printed.png"))

    assert result.text == ""
    assert result.confidence is None
    assert any(w.code == "PAGE_HAS_NO_TEXT" for w in result.warnings)


def test_empty_bytes_raises_empty_input_error():
    processor = ImageProcessor(ocr_engine=FakeOCREngine())
    with pytest.raises(EmptyInputError):
        processor.process(b"")


def test_corrupted_image_raises_corrupted_file_error():
    processor = ImageProcessor(ocr_engine=FakeOCREngine())
    with pytest.raises(CorruptedFileError):
        processor.process(load_image_fixture("corrupted.png"))


def test_unsupported_image_type_raises_corrupted_file_error():
    processor = ImageProcessor(ocr_engine=FakeOCREngine())
    with pytest.raises(CorruptedFileError):
        processor.process(load_image_fixture("unsupported_type.png"))


def test_ocr_failure_becomes_domain_error_not_raw_exception():
    engine = FakeOCREngine(exception=OCRFailedError("The OCR engine is unavailable."))
    processor = ImageProcessor(ocr_engine=engine)

    with pytest.raises(OCRFailedError):
        processor.process(load_image_fixture("clear_printed.png"))
