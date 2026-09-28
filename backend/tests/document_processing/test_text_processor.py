import pytest

from app.core.enums import DocumentSourceType
from app.core.exceptions import CorruptedFileError, EmptyInputError
from app.document_processing.interfaces import ExtractionConfidence
from app.document_processing.text_processor import TextProcessor


@pytest.fixture()
def processor() -> TextProcessor:
    return TextProcessor()


def test_normal_text(processor):
    result = processor.process("Patient reports mild headache.".encode("utf-8"))

    assert result.document_type == DocumentSourceType.TEXT
    assert result.text == "Patient reports mild headache."
    assert result.page_count is None
    assert result.confidence == ExtractionConfidence.HIGH
    assert result.requires_ocr is False
    assert result.warnings == []


def test_empty_input_raises(processor):
    with pytest.raises(EmptyInputError):
        processor.process(b"")


def test_whitespace_only_input_raises(processor):
    with pytest.raises(EmptyInputError):
        processor.process("   \n\t  \n  ".encode("utf-8"))


def test_unicode_text_is_preserved(processor):
    raw = "Café ünicode note: 头痛 (headache), synthetic 🏥 data."
    result = processor.process(raw.encode("utf-8"))

    assert result.text == raw


def test_excessive_whitespace_is_normalized(processor):
    raw = "Line one.\r\n\r\n\r\n\r\nLine   two   has    gaps.\r\nLine three.   "
    result = processor.process(raw.encode("utf-8"))

    assert result.text == "Line one.\n\nLine two has gaps.\nLine three."


def test_invalid_utf8_raises_corrupted_file_error(processor):
    with pytest.raises(CorruptedFileError):
        processor.process(b"\xff\xfe\x00\x01invalid utf-8 bytes")
