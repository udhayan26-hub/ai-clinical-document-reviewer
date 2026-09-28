"""AI/ML pipeline contracts: EXTRACT -> GENERATE -> VALIDATE.

`AIProvider` is the *only* thing `app.ai.pipeline.ClinicalAnalysisPipeline`
depends on for the two LLM-backed stages — never a specific model or
provider SDK. `ClinicalReportValidator` is deliberately a **separate**
interface, not a method on `AIProvider`: validation must be deterministic
and independent of whichever provider produced the draft report (see
docs/decisions/008-ai-pipeline.md) — an `AIProvider` is never asked to
validate its own output.

Concrete `AIProvider` implementations live under `app.ai.providers`
(currently: `UnconfiguredAIProvider`, the safe default when no real
provider is configured — see `app.ai.factory`) and are selected by the
`AI_PROVIDER` / `AI_MODEL_NAME` settings in `app.core.config`. Swapping
providers means adding a new implementation of `AIProvider` — it must
never require changes to `app.api`, `app.services`, or the pipeline
orchestrator.

No prompt or provider SDK call lives in this module.
"""

from abc import ABC, abstractmethod
from typing import Any

from app.ai.schemas import ExtractionResult, ValidationResult
from app.document_processing.interfaces import NormalizedDocument


class AIProvider(ABC):
    """A single AI/LLM backend capable of the two generative pipeline
    stages. `extract` and `generate` are grouped on one interface (rather
    than two, as in earlier drafts of this contract) because a real
    provider implementation shares one client/credential/model
    configuration across both calls — see docs/decisions/008-ai-pipeline.md
    "Design decisions" for why this consolidation was made.

    Does NOT own: OCR/text extraction (`app.document_processing`),
    deterministic validation of its own output (`ClinicalReportValidator`,
    below — an `AIProvider` is never trusted to grade itself).
    """

    @abstractmethod
    def extract(self, document: NormalizedDocument) -> ExtractionResult:
        """Pull structured clinical facts out of `document.text`. Raise
        `app.core.exceptions.AIExtractionFailedError` on provider failure
        (timeout, API error, malformed provider response, etc.).
        """
        raise NotImplementedError

    @abstractmethod
    def generate(self, extraction: ExtractionResult) -> dict[str, Any]:
        """Assemble a draft clinical report from `extraction`. Returns a
        raw, provider-specific dict shaped like
        `app.schemas.clinical_report.ClinicalReport` but NOT guaranteed to
        satisfy it yet — that gate is `ClinicalReportValidator`, not this
        method. Raise `app.core.exceptions.AIGenerationFailedError` on
        provider failure.
        """
        raise NotImplementedError


class ClinicalReportValidator(ABC):
    """The deterministic, non-LLM gate between a draft report and a
    trusted `ClinicalReport`. Never raises — always returns a
    `ValidationResult` (status VALID or INVALID plus any issues found),
    even for completely malformed input; the pipeline orchestrator decides
    whether an INVALID result should raise
    `app.core.exceptions.ReportValidationFailedError`.

    Does NOT own: generation itself, and must not silently invent values
    to make a report pass — repair, if any, is limited to structural
    fixes; it never fabricates clinical content or evidence.
    """

    @abstractmethod
    def validate(
        self, draft_report: dict[str, Any], extraction: ExtractionResult, source_text: str
    ) -> ValidationResult:
        raise NotImplementedError
