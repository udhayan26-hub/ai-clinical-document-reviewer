"""Domain contracts for the AI/ML pipeline: EXTRACT -> GENERATE -> VALIDATE.

These are plain Pydantic models with no FastAPI/SQLAlchemy/provider-SDK
dependency, importable by `app.ai.interfaces`, any `AIProvider`/
`ClinicalReportValidator` implementation, and `app.ai.pipeline`.

Reuses `app.schemas.clinical_report.{ConfidenceLevel, EvidenceSpan}` rather
than redefining an equivalent shape — the "how confident, cite the
evidence" pattern established for the final report applies identically to
a single extracted fact.
"""

from enum import Enum

from pydantic import BaseModel, Field, model_validator

from app.schemas.clinical_report import ClinicalReport, ConfidenceLevel, EvidenceSpan


class ClinicalFactCategory(str, Enum):
    """What kind of thing a `ClinicalFact` records. Mirrors the section
    names already used by `ClinicalReport` where one exists, plus the
    extraction-only categories (identifiers, document metadata,
    investigations, lab results, procedures, history) the report doesn't
    have a dedicated section for yet.
    """

    PATIENT_IDENTIFIER = "PATIENT_IDENTIFIER"
    DOCUMENT_METADATA = "DOCUMENT_METADATA"
    OBSERVATION = "OBSERVATION"
    SYMPTOM = "SYMPTOM"
    DIAGNOSIS = "DIAGNOSIS"
    MEDICATION = "MEDICATION"
    ALLERGY = "ALLERGY"
    INVESTIGATION = "INVESTIGATION"
    LAB_RESULT = "LAB_RESULT"
    VITAL_SIGN = "VITAL_SIGN"
    PROCEDURE = "PROCEDURE"
    HISTORY = "HISTORY"


class ClinicalFact(BaseModel):
    """One atomic piece of information pulled out of a document's
    normalized text. Deliberately flat (category + text value) rather
    than a rich per-category sub-schema — structuring further into the
    report's per-section shape (e.g. splitting a medication into
    name/dosage/frequency) is `GENERATE`'s job, not extraction's.
    """

    category: ClinicalFactCategory
    value: str = Field(..., min_length=1, description="The extracted fact as text, e.g. 'Ibuprofen 400mg'.")
    evidence: list[EvidenceSpan] = Field(
        default_factory=list, description="Verbatim quotes from the source document supporting this fact."
    )
    confidence: ConfidenceLevel = ConfidenceLevel.LOW
    inferred: bool = Field(
        default=False, description="True if summarized/interpreted rather than directly stated in the source."
    )

    @model_validator(mode="after")
    def _evidence_required_unless_inferred(self) -> "ClinicalFact":
        if not self.inferred and not self.evidence:
            raise ValueError("A non-inferred fact must cite at least one evidence span.")
        return self


class ExtractionResult(BaseModel):
    """Output of the EXTRACT stage — the structured material GENERATE
    consumes. Never contains prose; every fact traces back to the source
    document via `ClinicalFact.evidence`.
    """

    facts: list[ClinicalFact] = Field(default_factory=list)
    missing_information: list[str] = Field(
        default_factory=list, description="Expected clinical information not found in the document."
    )
    notes: list[str] = Field(default_factory=list, description="Free-form extractor caveats not tied to one fact.")


class ValidationStatus(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"


class ValidationIssueSeverity(str, Enum):
    ERROR = "ERROR"  # invalidates the report — pipeline must not return it as COMPLETED
    WARNING = "WARNING"  # recorded, does not by itself invalidate the report


class ValidationIssueCode(str, Enum):
    SCHEMA_INVALID = "SCHEMA_INVALID"
    EVIDENCE_NOT_GROUNDED = "EVIDENCE_NOT_GROUNDED"
    MISSING_INFORMATION_NOT_REPRESENTED = "MISSING_INFORMATION_NOT_REPRESENTED"
    CONFIDENCE_NOT_PRESERVED = "CONFIDENCE_NOT_PRESERVED"


class ValidationIssue(BaseModel):
    code: ValidationIssueCode
    severity: ValidationIssueSeverity
    message: str
    field_path: str | None = Field(default=None, description='e.g. "diagnoses[0]", when applicable.')


class ValidationResult(BaseModel):
    """Output of the VALIDATE stage. `report` is populated only when
    `status == VALID` — a caller must check `status`, never infer it from
    whether `report` happens to be set.
    """

    status: ValidationStatus
    report: ClinicalReport | None = None
    issues: list[ValidationIssue] = Field(default_factory=list)


class PipelineResult(BaseModel):
    """Returned by `ClinicalAnalysisPipeline.run()` on a fully successful
    run only — any stage failure raises instead (see
    `app.core.exceptions`), so `validation.status` here is always VALID.
    `validation.issues` may still contain WARNING-severity entries worth
    persisting even on success.
    """

    extraction: ExtractionResult
    validation: ValidationResult
