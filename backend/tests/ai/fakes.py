"""Deterministic test doubles for the AI/ML pipeline.

Used by every pipeline/service test instead of a real LLM call — per the
project's testing requirements (docs/testing/README.md), no test may
require network access or an external AI API.
"""

from typing import Any

from app.ai.interfaces import AIProvider, ClinicalReportValidator
from app.ai.schemas import ExtractionResult, ValidationResult


class FakeAIProvider(AIProvider):
    def __init__(
        self,
        extraction_result: ExtractionResult | None = None,
        extraction_exception: Exception | None = None,
        draft_report: dict[str, Any] | None = None,
        generation_exception: Exception | None = None,
    ) -> None:
        self._extraction_result = extraction_result
        self._extraction_exception = extraction_exception
        self._draft_report = draft_report
        self._generation_exception = generation_exception
        self.extract_calls: list[Any] = []
        self.generate_calls: list[ExtractionResult] = []

    def extract(self, document) -> ExtractionResult:
        self.extract_calls.append(document)
        if self._extraction_exception is not None:
            raise self._extraction_exception
        return self._extraction_result if self._extraction_result is not None else ExtractionResult()

    def generate(self, extraction: ExtractionResult) -> dict[str, Any]:
        self.generate_calls.append(extraction)
        if self._generation_exception is not None:
            raise self._generation_exception
        return self._draft_report if self._draft_report is not None else {}


class SpyingValidator(ClinicalReportValidator):
    """Wraps a real validator and records whether/how many times it was
    called — used to prove the pipeline cannot skip the VALIDATE stage.
    """

    def __init__(self, wrapped: ClinicalReportValidator) -> None:
        self._wrapped = wrapped
        self.call_count = 0

    def validate(self, draft_report, extraction, source_text) -> ValidationResult:
        self.call_count += 1
        return self._wrapped.validate(draft_report, extraction, source_text)
