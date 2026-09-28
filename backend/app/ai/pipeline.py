"""The EXTRACT -> GENERATE -> VALIDATE orchestrator.

This is the only place that sequences the three AI/ML pipeline stages.
`app.services.analysis_service.AnalysisService` calls this; nothing below
it (the `AIProvider`/`ClinicalReportValidator` implementations) knows
about the others or about persistence/HTTP.
"""

import logging
from typing import Any

from app.ai.evidence_grounding import find_ungrounded_quotes
from app.ai.interfaces import AIProvider, ClinicalReportValidator
from app.ai.schemas import ExtractionResult, PipelineResult, ValidationIssueSeverity, ValidationStatus
from app.core.exceptions import (
    AIExtractionFailedError,
    AIGenerationFailedError,
    AppError,
    EvidenceMismatchError,
    ReportValidationFailedError,
)
from app.document_processing.interfaces import NormalizedDocument

logger = logging.getLogger("app.ai.pipeline")


class ClinicalAnalysisPipeline:
    """Does NOT own: what a provider does internally, or how validation
    decides pass/fail — only the order stages run in and what happens
    when one fails. Never logs `document.text`, extracted facts, or
    generated report content — only stage names and outcome/error codes
    (see docs/architecture/system-architecture.md "Observability").
    """

    def __init__(self, provider: AIProvider, validator: ClinicalReportValidator) -> None:
        self._provider = provider
        self._validator = validator

    def run(self, document: NormalizedDocument) -> PipelineResult:
        extraction = self._extract(document)
        self._validate_extraction_structure(extraction, document.text)
        draft_report = self._generate(extraction)
        validation = self._validator.validate(draft_report, extraction, document.text)

        if validation.status == ValidationStatus.INVALID:
            error_codes = sorted(
                {
                    issue.code.value
                    for issue in validation.issues
                    if issue.severity == ValidationIssueSeverity.ERROR
                }
            )
            logger.info("pipeline validation rejected report: %s", ", ".join(error_codes))
            raise ReportValidationFailedError(
                f"Generated report failed validation: {', '.join(error_codes) or 'unknown reason'}."
            )

        logger.info("pipeline completed: %d fact(s), %d validation issue(s)", len(extraction.facts), len(validation.issues))
        return PipelineResult(extraction=extraction, validation=validation)

    def _extract(self, document: NormalizedDocument) -> ExtractionResult:
        try:
            return self._provider.extract(document)
        except AppError:
            raise
        except Exception as exc:
            raise AIExtractionFailedError("The AI provider raised an unexpected error during extraction.") from exc

    def _validate_extraction_structure(self, extraction: ExtractionResult, source_text: str) -> None:
        """Catch a hallucinating/ungrounded extraction before spending a
        GENERATE call on it — the same evidence-grounding rule GENERATE's
        output will later be held to, applied one stage earlier.
        """
        quotes = [span.quote for fact in extraction.facts for span in fact.evidence]
        ungrounded = find_ungrounded_quotes(quotes, source_text)
        if ungrounded:
            raise EvidenceMismatchError(
                f"{len(ungrounded)} extracted fact(s) cite evidence not found verbatim in the source document."
            )

    def _generate(self, extraction: ExtractionResult) -> dict[str, Any]:
        try:
            return self._provider.generate(extraction)
        except AppError:
            raise
        except Exception as exc:
            raise AIGenerationFailedError("The AI provider raised an unexpected error during generation.") from exc
