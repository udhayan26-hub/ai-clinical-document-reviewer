"""Deterministic test double for `OCREngine`.

Used by every OCR-related test instead of the real `TesseractOCREngine` so
the suite never depends on a real OCR binary, network access, or
nondeterministic recognition output — per the project's testing
requirements (see docs/testing/README.md).
"""

from app.document_processing.interfaces import OCREngine, OCRResult


class FakeOCREngine(OCREngine):
    def __init__(
        self,
        result: OCRResult | None = None,
        results: list[OCRResult | Exception] | None = None,
        exception: Exception | None = None,
    ) -> None:
        """Configure exactly one of:
        - `result`: return this same OCRResult for every call.
        - `results`: return these in order, one per call (for multi-page/
          multi-image tests where each call should see different input) —
          an entry may be an `Exception` instance to simulate that one
          specific call failing while others succeed (e.g. a multi-page
          PDF where only one page's OCR fails).
        - `exception`: raise this on every call (to simulate OCR failure).
        """
        self._result = result
        self._results = list(results) if results is not None else None
        self._exception = exception
        self.calls: list[bytes] = []

    def recognize(self, image_bytes: bytes) -> OCRResult:
        self.calls.append(image_bytes)
        if self._exception is not None:
            raise self._exception
        if self._results is not None:
            item = self._results.pop(0)
            if isinstance(item, Exception):
                raise item
            return item
        return self._result if self._result is not None else OCRResult(text="", confidence=None)
