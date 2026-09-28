"""Shared, pre-OCR image-quality heuristic used by both `ImageProcessor`
and `PDFProcessor` (for embedded page images) — kept separate so the two
processors apply exactly the same rule rather than duplicating it.

This is a deliberately coarse, documented heuristic based on pixel
dimensions alone (no scanner DPI metadata is reliably available), and is
independent of the OCR engine's own confidence signal (`OCR_LOW_CONFIDENCE`,
reported by the engine after recognition). The two warnings answer
different questions: this one asks "does the input look too small to OCR
well?" before OCR even runs; `OCR_LOW_CONFIDENCE` asks "how sure was the
engine about what it read?" after the fact.
"""

from PIL import Image

from app.document_processing.interfaces import ExtractionWarning

MIN_DIMENSION_PX = 200


def assess_image_quality(image: Image.Image) -> list[ExtractionWarning]:
    width, height = image.size
    if width < MIN_DIMENSION_PX or height < MIN_DIMENSION_PX:
        return [
            ExtractionWarning(
                code="IMAGE_QUALITY_LOW",
                message=(
                    f"Image resolution ({width}x{height}px) is below the "
                    f"{MIN_DIMENSION_PX}px minimum on at least one dimension; "
                    "OCR accuracy may be reduced."
                ),
            )
        ]
    return []
