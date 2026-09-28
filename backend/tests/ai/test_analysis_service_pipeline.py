"""Integration tests for AnalysisService.run_pipeline() — the existing
service boundary the AI pipeline is wired into. Uses the same in-memory
SQLite db_session fixture as the rest of the API test suite
(backend/tests/conftest.py); a FakeAIProvider stands in for any real LLM.
"""

from app.core.enums import AnalysisStatus, ProcessingEventType
from app.services.analysis_service import AnalysisService
from tests.ai.builders import SOURCE_TEXT, build_grounded_extraction, build_valid_draft_report
from tests.ai.fakes import FakeAIProvider
from tests.document_processing.fixture_paths import load_pdf_fixture


def make_service(db_session, provider: FakeAIProvider) -> AnalysisService:
    return AnalysisService(db_session, ai_provider=provider)


def test_run_pipeline_completes_successfully_for_text_analysis(db_session):
    provider = FakeAIProvider(extraction_result=build_grounded_extraction(), draft_report=build_valid_draft_report())
    service = make_service(db_session, provider)
    analysis = service.create_analysis(text=SOURCE_TEXT, filename=None, content_type=None, file_bytes=None)

    completed = service.run_pipeline(analysis.id)

    assert completed.status == AnalysisStatus.COMPLETED
    assert completed.error_code is None
    report = service.get_report(analysis.id)
    assert report.report_summary
    assert report.ai_provider == service.settings.ai_provider


def test_run_pipeline_completes_successfully_for_pdf_analysis(db_session):
    """Raw PDF bytes are persisted at upload time (see
    docs/decisions/005-storage.md) and read back during run_pipeline, so a
    real PDF reaches the same extract -> generate -> validate -> COMPLETED
    pipeline as a TEXT analysis."""
    provider = FakeAIProvider(extraction_result=build_grounded_extraction(), draft_report=build_valid_draft_report())
    service = make_service(db_session, provider)
    pdf_bytes = load_pdf_fixture("valid_text_grounded.pdf")
    analysis = service.create_analysis(text=None, filename="note.pdf", content_type="application/pdf", file_bytes=pdf_bytes)

    completed = service.run_pipeline(analysis.id)

    assert completed.status == AnalysisStatus.COMPLETED
    assert completed.error_code is None
    report = service.get_report(analysis.id)
    assert report.report_summary


def test_run_pipeline_fails_cleanly_for_corrupted_pdf_bytes(db_session):
    """Malformed file content must still fail cleanly and never reach the
    AI provider, independent of whether the bytes were persisted."""
    provider = FakeAIProvider()
    service = make_service(db_session, provider)
    pdf_bytes = b"%PDF-1.4 minimal placeholder content for a non-empty upload"
    analysis = service.create_analysis(text=None, filename="note.pdf", content_type="application/pdf", file_bytes=pdf_bytes)

    failed = service.run_pipeline(analysis.id)

    assert failed.status == AnalysisStatus.FAILED
    assert failed.error_code == "CORRUPTED_FILE"
    assert provider.extract_calls == []  # never even reached the AI provider


def test_run_pipeline_validation_rejection_sets_failed_status_with_clear_code(db_session):
    draft = build_valid_draft_report()
    draft["diagnoses"][0]["evidence"] = [{"quote": "a claim with no basis in the document"}]
    provider = FakeAIProvider(extraction_result=build_grounded_extraction(), draft_report=draft)
    service = make_service(db_session, provider)
    analysis = service.create_analysis(text=SOURCE_TEXT, filename=None, content_type=None, file_bytes=None)

    failed = service.run_pipeline(analysis.id)

    assert failed.status == AnalysisStatus.FAILED
    assert failed.error_code == "REPORT_VALIDATION_FAILED"


def test_run_pipeline_records_processing_events_for_each_stage(db_session):
    provider = FakeAIProvider(extraction_result=build_grounded_extraction(), draft_report=build_valid_draft_report())
    service = make_service(db_session, provider)
    analysis = service.create_analysis(text=SOURCE_TEXT, filename=None, content_type=None, file_bytes=None)

    service.run_pipeline(analysis.id)

    events = service.events.list_for_analysis(analysis.id)
    event_types = [event.event_type for event in events]
    assert ProcessingEventType.EXTRACTION_STARTED in event_types
    assert ProcessingEventType.EXTRACTION_COMPLETED in event_types
    assert ProcessingEventType.AI_ANALYSIS_STARTED in event_types
    assert ProcessingEventType.AI_ANALYSIS_COMPLETED in event_types
    assert ProcessingEventType.REPORT_PERSISTED in event_types


def test_run_pipeline_never_raises_out_of_the_service(db_session):
    """run_pipeline() must always return the (failed) Analysis rather than
    letting an exception propagate to the caller."""
    provider = FakeAIProvider(extraction_exception=RuntimeError("simulated provider crash"))
    service = make_service(db_session, provider)
    analysis = service.create_analysis(text=SOURCE_TEXT, filename=None, content_type=None, file_bytes=None)

    result = service.run_pipeline(analysis.id)  # must not raise

    assert result.status == AnalysisStatus.FAILED
    assert result.error_code == "AI_EXTRACTION_FAILED"
