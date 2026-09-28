import pytest

from app.ai.factory import get_default_validator
from app.ai.pipeline import ClinicalAnalysisPipeline
from app.ai.schemas import ExtractionResult, ValidationStatus
from app.core.exceptions import (
    AIExtractionFailedError,
    AIGenerationFailedError,
    EvidenceMismatchError,
    ReportValidationFailedError,
)
from app.schemas.clinical_report import EvidenceSpan
from tests.ai.builders import build_grounded_extraction, build_normalized_document, build_valid_draft_report
from tests.ai.fakes import FakeAIProvider, SpyingValidator


def make_pipeline(provider, validator=None) -> ClinicalAnalysisPipeline:
    return ClinicalAnalysisPipeline(provider, validator or get_default_validator())


def test_successful_pipeline_end_to_end():
    provider = FakeAIProvider(extraction_result=build_grounded_extraction(), draft_report=build_valid_draft_report())

    result = make_pipeline(provider).run(build_normalized_document())

    assert len(result.extraction.facts) == 2
    assert result.validation.status == ValidationStatus.VALID
    assert result.validation.report.report_summary


def test_extraction_failure_raised_by_provider_propagates_as_extraction_error():
    provider = FakeAIProvider(extraction_exception=RuntimeError("provider timeout"))

    with pytest.raises(AIExtractionFailedError):
        make_pipeline(provider).run(build_normalized_document())


def test_malformed_extraction_with_fabricated_evidence_is_rejected_before_generation():
    bad_extraction = ExtractionResult(
        facts=[
            *build_grounded_extraction().facts,
        ]
    )
    # Tamper with one fact's evidence so it no longer appears in the source text.
    bad_extraction.facts[0].evidence = [EvidenceSpan(quote="a symptom that was never mentioned")]
    provider = FakeAIProvider(extraction_result=bad_extraction, draft_report=build_valid_draft_report())

    with pytest.raises(EvidenceMismatchError):
        make_pipeline(provider).run(build_normalized_document())

    assert provider.generate_calls == []  # GENERATE must never run on a rejected extraction


def test_generation_failure_raised_by_provider_propagates_as_generation_error():
    provider = FakeAIProvider(extraction_result=build_grounded_extraction(), generation_exception=RuntimeError("provider error"))

    with pytest.raises(AIGenerationFailedError):
        make_pipeline(provider).run(build_normalized_document())


def test_validation_rejection_of_unsupported_claim_propagates_as_validation_error():
    draft = build_valid_draft_report()
    draft["diagnoses"][0]["evidence"] = [{"quote": "a claim with no basis in the document"}]
    provider = FakeAIProvider(extraction_result=build_grounded_extraction(), draft_report=draft)

    with pytest.raises(ReportValidationFailedError):
        make_pipeline(provider).run(build_normalized_document())


def test_pipeline_cannot_skip_the_validation_stage():
    provider = FakeAIProvider(extraction_result=build_grounded_extraction(), draft_report=build_valid_draft_report())
    spy = SpyingValidator(get_default_validator())

    make_pipeline(provider, spy).run(build_normalized_document())

    assert spy.call_count == 1


def test_pipeline_cannot_skip_validation_even_when_it_would_reject():
    """The validator must run (and its rejection must propagate) even
    though nothing about the extract/generate stages themselves failed."""
    draft = build_valid_draft_report()
    draft["diagnoses"][0]["evidence"] = [{"quote": "unsupported"}]
    provider = FakeAIProvider(extraction_result=build_grounded_extraction(), draft_report=draft)
    spy = SpyingValidator(get_default_validator())

    with pytest.raises(ReportValidationFailedError):
        make_pipeline(provider, spy).run(build_normalized_document())

    assert spy.call_count == 1


def test_pipeline_output_is_deterministic():
    provider_a = FakeAIProvider(extraction_result=build_grounded_extraction(), draft_report=build_valid_draft_report())
    provider_b = FakeAIProvider(extraction_result=build_grounded_extraction(), draft_report=build_valid_draft_report())

    result_a = make_pipeline(provider_a).run(build_normalized_document())
    result_b = make_pipeline(provider_b).run(build_normalized_document())

    assert result_a.validation.report.model_dump() == result_b.validation.report.model_dump()


def test_provider_selection_returns_unconfigured_provider_for_placeholder_setting():
    from app.ai.factory import get_default_ai_provider
    from app.ai.providers.unconfigured import UnconfiguredAIProvider

    get_default_ai_provider.cache_clear()
    try:
        provider = get_default_ai_provider()
        assert isinstance(provider, UnconfiguredAIProvider)
    finally:
        get_default_ai_provider.cache_clear()


def test_provider_selection_raises_for_unknown_provider_setting(monkeypatch):
    from app.ai import factory as ai_factory
    from app.core.config import Settings
    from app.core.exceptions import UnsupportedAIProviderError

    monkeypatch.setattr(ai_factory, "get_settings", lambda: Settings(ai_provider="some-unknown-vendor"))
    ai_factory.get_default_ai_provider.cache_clear()
    try:
        with pytest.raises(UnsupportedAIProviderError):
            ai_factory.get_default_ai_provider()
    finally:
        ai_factory.get_default_ai_provider.cache_clear()
