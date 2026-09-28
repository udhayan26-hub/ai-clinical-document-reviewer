"""AI/ML pipeline contracts.

These interfaces are the *only* thing `app.services.analysis_service`
depends on for clinical analysis — never a specific model or provider
SDK. Concrete implementations live under the top-level `ml/` package
(kept independent of FastAPI/SQLAlchemy) and are wired in via
`app.ai.factory` (not yet implemented), selected by the `AI_PROVIDER` /
`AI_MODEL_NAME` settings in `app.core.config`. Swapping providers means
adding a new implementation of these interfaces — it must never require
changes to `app.api` or `app.services`.

No implementation, prompt, or provider SDK call lives in this module.
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.clinical_report import ClinicalReport


class ClinicalExtractionResult(BaseModel):
    """Intermediate, provider-agnostic representation of clinical facts
    pulled out of normalized text — the input to `ClinicalReportGenerator`.
    Deliberately looser than `ClinicalReport`: this is raw material, not
    yet assembled into the final report contract or validated against it.
    """

    raw_entities: dict[str, Any] = Field(
        default_factory=dict, description="Provider-specific intermediate extraction payload."
    )
    notes: list[str] = Field(default_factory=list, description="Free-form extraction notes/warnings.")


class ClinicalInformationExtractor(ABC):
    """Pulls clinical facts (symptoms, meds, vitals, etc.) out of
    normalized document text.

    Does NOT own: OCR/text extraction (see `app.document_processing`),
    assembling the final report narrative (see `ClinicalReportGenerator`),
    or schema validation (see `StructuredOutputValidator`).
    """

    @abstractmethod
    def extract(self, normalized_text: str) -> ClinicalExtractionResult:
        """Raise `app.core.exceptions.AIProcessingError` on provider
        failure (timeout, API error, etc.).
        """
        raise NotImplementedError


class ClinicalReportGenerator(ABC):
    """Assembles a `ClinicalReport` from a `ClinicalExtractionResult` (and
    the original normalized text, for evidence citation).

    Does NOT own: schema enforcement of its own output — every generator
    implementation's raw output must still pass through
    `StructuredOutputValidator` before it is trusted or persisted.
    """

    @abstractmethod
    def generate(self, extraction: ClinicalExtractionResult, normalized_text: str) -> ClinicalReport:
        """Raise `app.core.exceptions.AIProcessingError` on provider
        failure.
        """
        raise NotImplementedError


class StructuredOutputValidator(ABC):
    """Final gate between AI output and the rest of the system: validates
    (and may attempt bounded repair of) a generator's raw output against
    the `ClinicalReport` contract.

    Does NOT own: generation itself, and must not silently invent values
    to satisfy the schema — repair is limited to structural fixes (e.g.
    coercing types, dropping unparsable fields into `missing_information`);
    it never fabricates clinical content.
    """

    @abstractmethod
    def validate(self, raw_output: Any) -> ClinicalReport:
        """Raise `app.core.exceptions.MalformedStructuredOutputError` if
        `raw_output` cannot be coerced into a valid `ClinicalReport`.
        """
        raise NotImplementedError
