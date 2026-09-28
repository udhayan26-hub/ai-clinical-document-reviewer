"""The one `ClinicalReportValidator` implementation: pure Python, no LLM
call, no network. See docs/decisions/008-ai-pipeline.md "Deterministic
Validation" for the checklist this implements and why each check exists.
"""

from typing import Any

from pydantic import ValidationError

from app.ai.evidence_grounding import find_ungrounded_quotes
from app.ai.interfaces import ClinicalReportValidator
from app.ai.schemas import (
    ExtractionResult,
    ValidationIssue,
    ValidationIssueCode,
    ValidationIssueSeverity,
    ValidationResult,
    ValidationStatus,
)
from app.schemas.clinical_report import ClinicalReport, ConfidenceLevel, SourcedFinding

_CONFIDENCE_RANK = {ConfidenceLevel.LOW: 0, ConfidenceLevel.MEDIUM: 1, ConfidenceLevel.HIGH: 2}


def _all_findings(report: ClinicalReport) -> list[SourcedFinding]:
    return [
        report.patient_information,
        *report.symptoms,
        *report.diagnoses,
        *report.medications,
        *report.vitals,
        *report.allergies,
        *report.clinical_observations,
        *report.clinical_concerns,
    ]


class DeterministicClinicalReportValidator(ClinicalReportValidator):
    def validate(
        self, draft_report: dict[str, Any], extraction: ExtractionResult, source_text: str
    ) -> ValidationResult:
        try:
            return self._validate(draft_report, extraction, source_text)
        except Exception:
            # A validator that itself crashes would take down the whole
            # pipeline for a reason having nothing to do with the report's
            # actual validity — always return a result instead.
            return ValidationResult(
                status=ValidationStatus.INVALID,
                issues=[
                    ValidationIssue(
                        code=ValidationIssueCode.SCHEMA_INVALID,
                        severity=ValidationIssueSeverity.ERROR,
                        message="Validation could not be completed due to an internal error.",
                    )
                ],
            )

    def _validate(
        self, draft_report: dict[str, Any], extraction: ExtractionResult, source_text: str
    ) -> ValidationResult:
        issues: list[ValidationIssue] = []

        try:
            report = ClinicalReport(**draft_report)
        except ValidationError as exc:
            for error in exc.errors():
                issues.append(
                    ValidationIssue(
                        code=ValidationIssueCode.SCHEMA_INVALID,
                        severity=ValidationIssueSeverity.ERROR,
                        message=error.get("msg", "Schema validation failed."),
                        field_path=".".join(str(part) for part in error.get("loc", ())) or None,
                    )
                )
            return ValidationResult(status=ValidationStatus.INVALID, issues=issues)

        findings = _all_findings(report)

        # 1. Evidence grounding: every cited quote must really be in the source.
        all_quotes = [span.quote for finding in findings for span in finding.evidence]
        for quote in find_ungrounded_quotes(all_quotes, source_text):
            issues.append(
                ValidationIssue(
                    code=ValidationIssueCode.EVIDENCE_NOT_GROUNDED,
                    severity=ValidationIssueSeverity.ERROR,
                    message="A cited evidence quote does not appear verbatim in the source document.",
                )
            )

        # 2. Missing information the extractor flagged must not be silently dropped.
        if extraction.missing_information and not report.missing_information:
            issues.append(
                ValidationIssue(
                    code=ValidationIssueCode.MISSING_INFORMATION_NOT_REPRESENTED,
                    severity=ValidationIssueSeverity.WARNING,
                    message="The extraction flagged missing information that the report does not represent.",
                    field_path="missing_information",
                )
            )

        # 3. A finding must not claim higher confidence than the fact(s) backing it.
        fact_confidence_by_quote: dict[str, ConfidenceLevel] = {
            span.quote: fact.confidence for fact in extraction.facts for span in fact.evidence
        }
        for finding in findings:
            for span in finding.evidence:
                fact_confidence = fact_confidence_by_quote.get(span.quote)
                if fact_confidence is None:
                    continue
                if _CONFIDENCE_RANK[finding.confidence] > _CONFIDENCE_RANK[fact_confidence]:
                    issues.append(
                        ValidationIssue(
                            code=ValidationIssueCode.CONFIDENCE_NOT_PRESERVED,
                            severity=ValidationIssueSeverity.WARNING,
                            message=(
                                f"A finding claims {finding.confidence.value} confidence but its source fact "
                                f"was only {fact_confidence.value}."
                            ),
                        )
                    )

        has_errors = any(issue.severity == ValidationIssueSeverity.ERROR for issue in issues)
        if has_errors:
            return ValidationResult(status=ValidationStatus.INVALID, issues=issues)

        return ValidationResult(status=ValidationStatus.VALID, report=report, issues=issues)
