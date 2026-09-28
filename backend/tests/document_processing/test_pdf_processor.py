import pytest

from app.core.enums import DocumentSourceType
from app.core.exceptions import CorruptedFileError, EmptyInputError
from app.document_processing.interfaces import ExtractionConfidence
from app.document_processing.pdf_processor import PDFProcessor
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
