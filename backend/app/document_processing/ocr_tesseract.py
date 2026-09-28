"""Tesseract-backed `OCREngine` implementation.

This is the *only* file in `document_processing` that imports
`pytesseract` — see `docs/decisions/007-ocr.md` for why Tesseract was
chosen and its known limitations (in particular: it is a printed-text
engine; handwriting accuracy is not reliable, see
`HANDWRITING_MAY_REQUIRE_SPECIALIZED_MODEL` raised by the callers of
this engine, not by this file — this class just reports what it found
and how confident it was).
"""

import io
from functools import lru_cache

import pytesseract
from PIL import Image

from app.core.config import get_settings
from app.core.exceptions import OCRFailedError
from app.document_processing.interfaces import (
    ExtractionConfidence,
    ExtractionWarning,
    OCREngine,
    OCRResult,
)

# Coarse, documented mapping from Tesseract's real per-word 0-100 confidence
# scores to the app's existing qualitative model. Not invented: it is a
# deterministic bucketing of a number the engine actually reports.
_HIGH_CONFIDENCE_THRESHOLD = 80.0
_MEDIUM_CONFIDENCE_THRESHOLD = 50.0

# Tesseract's bundled models are trained on printed text; handwriting
# recognition is known to be unreliable. This is an engine-specific fact,
# not a general OCR limitation, so it is attached here — to this engine's
# OCRResult — rather than hardcoded into ImageProcessor/PDFProcessor. A
# future handwriting-capable OCREngine implementation would simply not
# emit this, with no changes needed anywhere else.
_HANDWRITING_WARNING = ExtractionWarning(
    code="HANDWRITING_MAY_REQUIRE_SPECIALIZED_MODEL",
    message=(
        "Text was recognized using Tesseract, which is optimized for printed "
        "text. If the source is handwritten, results may be inaccurate or "
        "incomplete, and a specialized handwriting-recognition model may be "
        "required for reliable results."
    ),
)


def _reconstruct_lines(data: dict) -> tuple[str, list[float]]:
    """Rebuild reading-order lines from `pytesseract.image_to_data`'s
    per-word rows (grouped by block/paragraph/line) instead of flattening
    every word into a single line, so multi-line layouts (e.g. vitals,
    one value per line) survive OCR.
    """
    lines: list[list[str]] = []
    current_key: tuple[int, int, int] | None = None
    confidences: list[float] = []

    n = len(data.get("text", []))
    for i in range(n):
        word = (data["text"][i] or "").strip()
        if not word:
            continue

        try:
            conf_value = float(data["conf"][i])
        except (TypeError, ValueError, KeyError, IndexError):
            conf_value = -1.0
        if conf_value >= 0:
            confidences.append(conf_value)

        key = (data.get("block_num", [0] * n)[i], data.get("par_num", [0] * n)[i], data.get("line_num", [0] * n)[i])
        if key != current_key:
            lines.append([])
            current_key = key
        lines[-1].append(word)

    text = "\n".join(" ".join(line) for line in lines)
    return text, confidences


def _bucket_confidence(confidences: list[float]) -> ExtractionConfidence | None:
    if not confidences:
        return None
    average = sum(confidences) / len(confidences)
    if average >= _HIGH_CONFIDENCE_THRESHOLD:
        return ExtractionConfidence.HIGH
    if average >= _MEDIUM_CONFIDENCE_THRESHOLD:
        return ExtractionConfidence.MEDIUM
    return ExtractionConfidence.LOW


def _build_warnings(confidence: ExtractionConfidence | None, has_text: bool) -> list[ExtractionWarning]:
    """Decide which warnings apply to one recognition result — split out
    from `recognize()` so this decision is unit-testable without a real
    OCR call (see tests/document_processing/test_ocr_tesseract.py).
    """
    warnings: list[ExtractionWarning] = []
    if confidence == ExtractionConfidence.LOW:
        warnings.append(
            ExtractionWarning(
                code="OCR_LOW_CONFIDENCE",
                message="The OCR engine reported low confidence in the recognized text.",
            )
        )
    if has_text:
        warnings.append(_HANDWRITING_WARNING)
    return warnings


class TesseractOCREngine(OCREngine):
    """Wraps the local Tesseract binary via `pytesseract`. No network
    call, no data leaves the machine.
    """

    def __init__(self, lang: str = "eng") -> None:
        self._lang = lang

    def recognize(self, image_bytes: bytes) -> OCRResult:
        try:
            image = Image.open(io.BytesIO(image_bytes))
            image.load()
        except Exception as exc:
            raise OCRFailedError("The image could not be decoded for OCR.") from exc

        try:
            data = pytesseract.image_to_data(image, lang=self._lang, output_type=pytesseract.Output.DICT)
        except Exception as exc:
            # Covers pytesseract.TesseractNotFoundError (binary missing) and
            # any other failure the engine/subprocess can raise — all mean
            # the same thing to a caller: OCR did not run successfully.
            raise OCRFailedError("OCR processing failed.") from exc

        text, confidences = _reconstruct_lines(data)
        confidence = _bucket_confidence(confidences)
        warnings = _build_warnings(confidence, has_text=bool(text.strip()))

        return OCRResult(text=text, confidence=confidence, warnings=warnings)


@lru_cache
def get_default_ocr_engine() -> OCREngine:
    """The OCR engine `document_processing.factory` wires into
    `ImageProcessor`/`PDFProcessor` by default. Reads `Settings.ocr_engine`
    so the concrete engine is a one-line config change, not a code change,
    to swap later — see docs/decisions/007-ocr.md.
    """
    settings = get_settings()
    if settings.ocr_engine == "tesseract":
        return TesseractOCREngine()
    raise ValueError(f"Unknown OCR_ENGINE setting: '{settings.ocr_engine}'.")
