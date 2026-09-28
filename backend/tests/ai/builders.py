"""Shared synthetic fixtures for AI pipeline tests. All content is
synthetic clinical text invented for testing — never real patient data.
"""

from typing import Any

from app.ai.schemas import ClinicalFact, ClinicalFactCategory, ExtractionResult
from app.core.enums import DocumentSourceType
from app.document_processing.interfaces import NormalizedDocument
from app.schemas.clinical_report import ConfidenceLevel, EvidenceSpan

SOURCE_TEXT = "Patient reports mild headache. Diagnosis: tension headache. No known allergies noted."


def build_normalized_document(text: str = SOURCE_TEXT) -> NormalizedDocument:
    return NormalizedDocument(document_type=DocumentSourceType.TEXT, text=text)


def build_grounded_extraction() -> ExtractionResult:
    """Facts whose evidence is a verbatim substring of SOURCE_TEXT."""
    return ExtractionResult(
        facts=[
            ClinicalFact(
                category=ClinicalFactCategory.SYMPTOM,
                value="mild headache",
                confidence=ConfidenceLevel.HIGH,
                evidence=[EvidenceSpan(quote="mild headache")],
            ),
            ClinicalFact(
                category=ClinicalFactCategory.DIAGNOSIS,
                value="tension headache",
                confidence=ConfidenceLevel.HIGH,
                evidence=[EvidenceSpan(quote="tension headache")],
            ),
        ]
    )


def build_valid_draft_report() -> dict[str, Any]:
    """A draft report whose findings are grounded in SOURCE_TEXT and match
    `build_grounded_extraction()`'s facts — passes deterministic validation.
    """
    return {
        "report_summary": "Synthetic patient with mild headache, diagnosed tension headache.",
        "patient_information": {"confidence": "LOW", "evidence": [], "inferred": True},
        "symptoms": [
            {
                "description": "mild headache",
                "confidence": "HIGH",
                "evidence": [{"quote": "mild headache"}],
                "inferred": False,
            }
        ],
        "diagnoses": [
            {
                "condition": "tension headache",
                "confidence": "HIGH",
                "evidence": [{"quote": "tension headache"}],
                "inferred": False,
            }
        ],
        # patient_information is inferred (no identifying info stated in the
        # synthetic source), which forces requires_review=True per
        # ClinicalReport's own validator — see app/schemas/clinical_report.py.
        "requires_review": True,
    }
