"""The structured clinical report contract.

This is the single source of truth for what the AI/ML pipeline must
produce (see `app.ai.interfaces.ClinicalReportGenerator`) and what the
`GET /api/v1/analyses/{analysis_id}/report` endpoint returns. The
frontend's `ClinicalReport` TypeScript type (frontend/src/types/clinicalReport.ts)
must be kept in sync with this module.

Design principle — "don't make unsupported information appear factual":
Every clinical finding (symptom, diagnosis, medication, vital, allergy,
observation, concern) carries `confidence`, `evidence` (verbatim quotes
from the extracted source text), and `inferred` (true when the model
summarized/inferred rather than quoting the source directly). A finding
with no evidence and `inferred=True` is a model's *interpretation*, not a
transcription of the document — API consumers and the frontend must
render these visibly differently (see docs/architecture/system-architecture.md,
"AI/ML Report Contract"). `requires_review` defaults to True and is
force-set whenever any low-confidence or inferred finding, inconsistency,
or missing-information gap exists — a human clinician must review
AI-generated output before any clinical use.
"""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class EvidenceSpan(BaseModel):
    """A verbatim excerpt from the analysis's extracted_text that supports
    a finding. Must be an actual substring of the source, not a
    paraphrase — paraphrased/summarized content belongs in the finding's
    own descriptive field, with `inferred=True` on the finding.
    """

    quote: str = Field(..., min_length=1, description="Verbatim excerpt from the extracted source text.")
    context: str | None = Field(default=None, description="Optional locator, e.g. a page or line reference.")


class SourcedFinding(BaseModel):
    """Common provenance fields mixed into every clinical finding type."""

    confidence: ConfidenceLevel = ConfidenceLevel.LOW
    evidence: list[EvidenceSpan] = Field(
        default_factory=list,
        description="Verbatim source excerpts supporting this finding. Empty only when inferred=True.",
    )
    inferred: bool = Field(
        default=False,
        description="True if this finding was inferred/summarized rather than directly stated in the source.",
    )

    @model_validator(mode="after")
    def _evidence_required_unless_inferred(self) -> "SourcedFinding":
        if not self.inferred and not self.evidence:
            raise ValueError("A non-inferred finding must cite at least one evidence span.")
        return self


class PatientInformation(SourcedFinding):
    name: str | None = None
    age: str | None = None
    sex: str | None = None
    date_of_birth: str | None = None
    additional_identifiers: dict[str, str] = Field(default_factory=dict)


class Symptom(SourcedFinding):
    description: str
    onset: str | None = None
    severity: str | None = None


class Diagnosis(SourcedFinding):
    condition: str
    icd10_code: str | None = None
    status: str | None = Field(default=None, description='e.g. "confirmed", "suspected", "ruled out".')


class Medication(SourcedFinding):
    name: str
    dosage: str | None = None
    frequency: str | None = None
    route: str | None = None


class VitalSign(SourcedFinding):
    name: str = Field(..., description="e.g. blood pressure, heart rate, temperature.")
    value: str
    unit: str | None = None
    recorded_at: str | None = None


class Allergy(SourcedFinding):
    substance: str
    reaction: str | None = None
    severity: str | None = None


class ClinicalObservation(SourcedFinding):
    description: str
    category: str | None = Field(default=None, description='e.g. "physical exam", "lab result".')


class ClinicalConcern(SourcedFinding):
    description: str
    severity: str | None = Field(default=None, description='e.g. "urgent", "routine".')
    recommended_action: str | None = None


class MissingInformationItem(BaseModel):
    field: str = Field(..., description="Name of the expected clinical field that could not be found.")
    reason: str | None = None


class PotentialInconsistency(BaseModel):
    description: str
    related_fields: list[str] = Field(default_factory=list)
    evidence: list[EvidenceSpan] = Field(default_factory=list)


class ClinicalReport(BaseModel):
    """The complete structured clinical report for one analysis."""

    model_config = ConfigDict(extra="forbid")

    report_summary: str = Field(..., description="Short, plain-language summary of the document's clinical content.")
    patient_information: PatientInformation
    symptoms: list[Symptom] = Field(default_factory=list)
    diagnoses: list[Diagnosis] = Field(default_factory=list)
    medications: list[Medication] = Field(default_factory=list)
    vitals: list[VitalSign] = Field(default_factory=list)
    allergies: list[Allergy] = Field(default_factory=list)
    clinical_observations: list[ClinicalObservation] = Field(default_factory=list)
    clinical_concerns: list[ClinicalConcern] = Field(default_factory=list)
    missing_information: list[MissingInformationItem] = Field(default_factory=list)
    potential_inconsistencies: list[PotentialInconsistency] = Field(default_factory=list)
    requires_review: bool = Field(
        default=True,
        description="Must remain True unless every finding is HIGH confidence, non-inferred, with no "
        "inconsistencies or missing information; enforced by validator below.",
    )

    @model_validator(mode="after")
    def _enforce_requires_review(self) -> "ClinicalReport":
        all_findings: list[SourcedFinding] = [
            self.patient_information,
            *self.symptoms,
            *self.diagnoses,
            *self.medications,
            *self.vitals,
            *self.allergies,
            *self.clinical_observations,
            *self.clinical_concerns,
        ]
        needs_review = (
            bool(self.potential_inconsistencies)
            or bool(self.missing_information)
            or any(f.inferred or f.confidence != ConfidenceLevel.HIGH for f in all_findings)
        )
        if needs_review and not self.requires_review:
            raise ValueError(
                "requires_review cannot be False while low/medium-confidence or inferred findings, "
                "missing information, or potential inconsistencies are present."
            )
        return self


class ClinicalReportResponse(BaseModel):
    """Response body for GET /api/v1/analyses/{analysis_id}/report."""

    analysis_id: uuid.UUID
    report: ClinicalReport
    ai_provider: str
    ai_model_name: str
    generated_at: datetime
