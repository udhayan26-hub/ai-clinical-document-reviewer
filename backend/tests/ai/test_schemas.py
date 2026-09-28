import pytest
from pydantic import ValidationError

from app.ai.schemas import ClinicalFact, ClinicalFactCategory, ExtractionResult
from app.schemas.clinical_report import ConfidenceLevel, EvidenceSpan


def test_non_inferred_fact_requires_evidence():
    with pytest.raises(ValidationError):
        ClinicalFact(category=ClinicalFactCategory.SYMPTOM, value="headache", confidence=ConfidenceLevel.HIGH, inferred=False, evidence=[])


def test_inferred_fact_may_omit_evidence():
    fact = ClinicalFact(category=ClinicalFactCategory.SYMPTOM, value="possible fatigue", confidence=ConfidenceLevel.LOW, inferred=True)
    assert fact.evidence == []


def test_fact_with_evidence_constructs():
    fact = ClinicalFact(
        category=ClinicalFactCategory.DIAGNOSIS,
        value="tension headache",
        confidence=ConfidenceLevel.HIGH,
        evidence=[EvidenceSpan(quote="tension headache")],
    )
    assert fact.category == ClinicalFactCategory.DIAGNOSIS


def test_extraction_result_defaults_to_empty():
    result = ExtractionResult()
    assert result.facts == []
    assert result.missing_information == []
    assert result.notes == []
