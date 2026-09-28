import pytest

from app.core.enums import DocumentSourceType
from app.core.exceptions import UnsupportedFileTypeError
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
    """Only checks selection (construction), never calls .process() here —
    PDF/IMAGE get the real default OCR engine from this factory, which
    talks to a real (possibly not installed) OCR binary. Actual
    processing behavior is tested against a FakeOCREngine in
    test_pdf_processor.py / test_image_processor.py.
    """
    processor = get_processor(source_type)

    assert isinstance(processor, expected_cls)


def test_pdf_and_image_processors_are_wired_with_an_ocr_engine():
    pdf_processor = get_processor(DocumentSourceType.PDF)
    image_processor = get_processor(DocumentSourceType.IMAGE)

    assert pdf_processor._ocr_engine is not None
    assert image_processor._ocr_engine is not None


def test_unsupported_source_type_raises_clear_error():
    """`DocumentSourceType` is an exhaustive enum with no unmapped member,
    but `get_processor` must still fail predictably — not with a raw
    KeyError/AttributeError — if it is ever called with something outside
    that enum (e.g. a stale/forward-compat value from a future migration).
    """
    with pytest.raises(UnsupportedFileTypeError):
        get_processor("AUDIO")  # type: ignore[arg-type]
