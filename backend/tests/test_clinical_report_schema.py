import pytest
from pydantic import ValidationError

from app.schemas.clinical_report import (
    ClinicalReport,
    ConfidenceLevel,
    EvidenceSpan,
    PatientInformation,
    Symptom,
)


def _minimal_report(**overrides):
    payload = {
        "report_summary": "Synthetic patient presenting with mild symptoms.",
        "patient_information": PatientInformation(
            name="Jane Doe",
            confidence=ConfidenceLevel.HIGH,
            evidence=[EvidenceSpan(quote="Patient: Jane Doe")],
        ),
        "requires_review": True,
    }
    payload.update(overrides)
    return ClinicalReport(**payload)


def test_minimal_valid_report_constructs():
    report = _minimal_report()
    assert report.requires_review is True
    assert report.symptoms == []


def test_non_inferred_finding_requires_evidence():
    with pytest.raises(ValidationError):
        Symptom(description="headache", confidence=ConfidenceLevel.HIGH, inferred=False, evidence=[])


def test_inferred_finding_may_omit_evidence():
    symptom = Symptom(description="possible fatigue", confidence=ConfidenceLevel.LOW, inferred=True, evidence=[])
    assert symptom.inferred is True


def test_requires_review_cannot_be_false_with_low_confidence_finding():
    with pytest.raises(ValidationError):
        _minimal_report(
            requires_review=False,
            symptoms=[
                Symptom(
                    description="mild cough",
                    confidence=ConfidenceLevel.LOW,
                    evidence=[EvidenceSpan(quote="mild cough noted")],
                )
            ],
        )


def test_requires_review_may_be_false_when_everything_is_high_confidence():
    report = _minimal_report(
        requires_review=False,
        patient_information=PatientInformation(
            name="Jane Doe",
            confidence=ConfidenceLevel.HIGH,
            evidence=[EvidenceSpan(quote="Patient: Jane Doe")],
        ),
    )
    assert report.requires_review is False
