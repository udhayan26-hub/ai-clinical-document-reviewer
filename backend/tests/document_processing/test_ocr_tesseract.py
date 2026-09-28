"""Unit tests for the pure helper functions behind `TesseractOCREngine`.

These test the confidence-bucketing, line-reconstruction, and warning
logic directly with synthetic data shaped like `pytesseract.image_to_data`'s
output — no image decoding, no OCR binary, no network. The one test that
does exercise `TesseractOCREngine.recognize()` for real
(`test_corrupted_image_bytes_raise_ocr_failed_without_binary`) only feeds
it undecodable bytes, which fail at the PIL-decode stage *before* the
Tesseract binary would ever be invoked — so it is deterministic whether
or not Tesseract is installed on the machine running the tests (unlike a
real successful-recognition test would be).
"""

import pytest

from app.core.exceptions import OCRFailedError
from app.document_processing.interfaces import ExtractionConfidence
from app.document_processing.ocr_tesseract import (
    TesseractOCREngine,
    _build_warnings,
    _bucket_confidence,
    _reconstruct_lines,
)


def _tesseract_data(
    text: list[str], conf: list[str], block_num: list[int], par_num: list[int], line_num: list[int]
) -> dict:
    return {"text": text, "conf": conf, "block_num": block_num, "par_num": par_num, "line_num": line_num}


def test_reconstruct_lines_groups_words_by_line_in_reading_order():
    data = _tesseract_data(
        text=["", "Hello", "world", "", "Second", "line"],
        conf=["-1", "95", "85", "-1", "60", "55"],
        block_num=[1, 1, 1, 1, 1, 1],
        par_num=[1, 1, 1, 1, 1, 1],
        line_num=[1, 1, 1, 1, 2, 2],
    )

    text, confidences = _reconstruct_lines(data)

    assert text == "Hello world\nSecond line"
    assert confidences == [95.0, 85.0, 60.0, 55.0]


def test_reconstruct_lines_ignores_blank_entries_entirely():
    data = _tesseract_data(
        text=["", "", ""],
        conf=["-1", "-1", "-1"],
        block_num=[1, 1, 1],
        par_num=[1, 1, 1],
        line_num=[1, 2, 3],
    )

    text, confidences = _reconstruct_lines(data)

    assert text == ""
    assert confidences == []


@pytest.mark.parametrize(
    ("confidences", "expected"),
    [
        ([], None),
        ([90.0, 85.0], ExtractionConfidence.HIGH),
        ([80.0], ExtractionConfidence.HIGH),
        ([79.9], ExtractionConfidence.MEDIUM),
        ([60.0, 55.0], ExtractionConfidence.MEDIUM),
        ([50.0], ExtractionConfidence.MEDIUM),
        ([49.9], ExtractionConfidence.LOW),
        ([10.0, 5.0], ExtractionConfidence.LOW),
    ],
)
def test_bucket_confidence_thresholds(confidences, expected):
    assert _bucket_confidence(confidences) == expected


def test_build_warnings_flags_low_confidence():
    warnings = _build_warnings(ExtractionConfidence.LOW, has_text=True)
    codes = [w.code for w in warnings]

    assert "OCR_LOW_CONFIDENCE" in codes
    assert "HANDWRITING_MAY_REQUIRE_SPECIALIZED_MODEL" in codes


def test_build_warnings_no_handwriting_warning_when_no_text_found():
    warnings = _build_warnings(None, has_text=False)

    assert warnings == []


def test_build_warnings_high_confidence_still_gets_handwriting_disclaimer():
    """The handwriting limitation is about the engine, not about how
    confident it was — it applies to every recognized result, high
    confidence included, since Tesseract can be very sure about a
    misread handwritten character."""
    warnings = _build_warnings(ExtractionConfidence.HIGH, has_text=True)

    codes = [w.code for w in warnings]
    assert "HANDWRITING_MAY_REQUIRE_SPECIALIZED_MODEL" in codes
    assert "OCR_LOW_CONFIDENCE" not in codes


def test_corrupted_image_bytes_raise_ocr_failed_without_binary():
    engine = TesseractOCREngine()

    with pytest.raises(OCRFailedError):
        engine.recognize(b"not a real image")
