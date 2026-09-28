from app.ai.factory import get_default_validator
from app.ai.schemas import ClinicalFact, ClinicalFactCategory, ExtractionResult, ValidationIssueCode, ValidationStatus
from app.schemas.clinical_report import ConfidenceLevel, EvidenceSpan
from tests.ai.builders import SOURCE_TEXT, build_grounded_extraction, build_valid_draft_report


def validator():
    return get_default_validator()


def test_valid_report_passes():
    result = validator().validate(build_valid_draft_report(), build_grounded_extraction(), SOURCE_TEXT)

    assert result.status == ValidationStatus.VALID
    assert result.report is not None
    assert result.issues == []


def test_schema_invalid_draft_is_rejected():
    """Missing the required report_summary field entirely."""
    draft = build_valid_draft_report()
    del draft["report_summary"]

    result = validator().validate(draft, build_grounded_extraction(), SOURCE_TEXT)

    assert result.status == ValidationStatus.INVALID
    assert result.report is None
    assert any(issue.code == ValidationIssueCode.SCHEMA_INVALID for issue in result.issues)


def test_missing_evidence_on_non_inferred_finding_is_rejected():
    """ClinicalReport's own schema forbids a non-inferred finding with no
    evidence — the validator must surface that as SCHEMA_INVALID, not
    silently accept an unsupported claim."""
    draft = build_valid_draft_report()
    draft["symptoms"][0]["evidence"] = []
    draft["symptoms"][0]["inferred"] = False

    result = validator().validate(draft, build_grounded_extraction(), SOURCE_TEXT)

    assert result.status == ValidationStatus.INVALID
    assert any(issue.code == ValidationIssueCode.SCHEMA_INVALID for issue in result.issues)


def test_unsupported_claim_with_fabricated_evidence_is_rejected():
    """The finding cites a quote that is well-formed but never appears in
    the source document — a fabricated/unsupported claim."""
    draft = build_valid_draft_report()
    draft["diagnoses"][0]["evidence"] = [{"quote": "patient has diabetes mellitus type 2"}]

    result = validator().validate(draft, build_grounded_extraction(), SOURCE_TEXT)

    assert result.status == ValidationStatus.INVALID
    assert any(issue.code == ValidationIssueCode.EVIDENCE_NOT_GROUNDED for issue in result.issues)


def test_missing_information_not_represented_is_a_warning_not_a_rejection():
    extraction = ExtractionResult(
        facts=build_grounded_extraction().facts,
        missing_information=["vital signs"],
    )
    draft = build_valid_draft_report()  # report.missing_information left empty

    result = validator().validate(draft, extraction, SOURCE_TEXT)

    assert result.status == ValidationStatus.VALID  # a warning, not an error
    assert any(issue.code == ValidationIssueCode.MISSING_INFORMATION_NOT_REPRESENTED for issue in result.issues)


def test_confidence_inflated_beyond_source_fact_is_flagged():
    extraction = ExtractionResult(
        facts=[
            ClinicalFact(
                category=ClinicalFactCategory.SYMPTOM,
                value="mild headache",
                confidence=ConfidenceLevel.LOW,
                evidence=[EvidenceSpan(quote="mild headache")],
            )
        ]
    )
    draft = build_valid_draft_report()
    draft["symptoms"][0]["confidence"] = "HIGH"  # claims more than the LOW-confidence source fact

    result = validator().validate(draft, extraction, SOURCE_TEXT)

    assert result.status == ValidationStatus.VALID  # a warning, not an error
    assert any(issue.code == ValidationIssueCode.CONFIDENCE_NOT_PRESERVED for issue in result.issues)


def test_potential_inconsistencies_can_be_represented():
    draft = build_valid_draft_report()
    draft["potential_inconsistencies"] = [
        {"description": "Diagnosis conflicts with a symptom-free note elsewhere.", "related_fields": ["diagnoses[0]"]}
    ]

    result = validator().validate(draft, build_grounded_extraction(), SOURCE_TEXT)

    assert result.status == ValidationStatus.VALID
    assert result.report.potential_inconsistencies[0].description.startswith("Diagnosis conflicts")


def test_validator_never_raises_on_completely_malformed_input():
    result = validator().validate({"not": "a report at all"}, ExtractionResult(), "")

    assert result.status == ValidationStatus.INVALID
