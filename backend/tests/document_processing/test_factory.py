import pytest

from app.core.enums import DocumentSourceType
from app.core.exceptions import OCRNotImplementedError, UnsupportedFileTypeError
from app.document_processing.factory import get_processor
from app.document_processing.image_processor import ImageProcessor
from app.document_processing.pdf_processor import PDFProcessor
from app.document_processing.text_processor import TextProcessor


@pytest.mark.parametrize(
    ("source_type", "expected_cls"),
    [
        (DocumentSourceType.TEXT, TextProcessor),
        (DocumentSourceType.PDF, PDFProcessor),
        (DocumentSourceType.IMAGE, ImageProcessor),
    ],
)
def test_processor_selection_returns_correct_type(source_type, expected_cls):
    processor = get_processor(source_type)

    assert isinstance(processor, expected_cls)


def test_image_processing_is_not_yet_supported():
    processor = get_processor(DocumentSourceType.IMAGE)

    with pytest.raises(OCRNotImplementedError):
        processor.process(b"fake image bytes")


def test_unsupported_source_type_raises_clear_error():
    """`DocumentSourceType` is an exhaustive enum with no unmapped member,
    but `get_processor` must still fail predictably — not with a raw
    KeyError/AttributeError — if it is ever called with something outside
    that enum (e.g. a stale/forward-compat value from a future migration).
    """
    with pytest.raises(UnsupportedFileTypeError):
        get_processor("AUDIO")  # type: ignore[arg-type]
