"""End-to-end proof that POST /api/v1/analyses now actually runs the
pipeline: create -> extract -> generate -> validate -> persist -> the
report is retrievable. Uses FakeAIProvider via dependency override — no
real LLM, no network, matching every other test in this suite.
"""

from fastapi.testclient import TestClient

from app.api.deps import get_analysis_service
from app.core.database import get_db
from app.main import app
from app.services.analysis_service import AnalysisService
from tests.ai.builders import SOURCE_TEXT, build_grounded_extraction, build_valid_draft_report
from tests.ai.fakes import FakeAIProvider


def test_post_analyses_runs_full_pipeline_and_report_is_retrievable(db_session):
    provider = FakeAIProvider(extraction_result=build_grounded_extraction(), draft_report=build_valid_draft_report())

    def override_get_db():
        yield db_session

    def override_get_service():
        yield AnalysisService(db_session, ai_provider=provider)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_analysis_service] = override_get_service
    try:
        with TestClient(app) as client:
            create_response = client.post("/api/v1/analyses", data={"text": SOURCE_TEXT})

            assert create_response.status_code == 201
            body = create_response.json()
            assert body["status"] == "COMPLETED"
            assert body["error_code"] is None
            assert body["report_available"] is True
            analysis_id = body["id"]

            report_response = client.get(f"/api/v1/analyses/{analysis_id}/report")

            assert report_response.status_code == 200
            report_body = report_response.json()
            assert report_body["analysis_id"] == analysis_id
            assert report_body["report"]["report_summary"]
            assert report_body["ai_provider"]

            # GET /analyses/{id} independently reflects the same completed state.
            get_response = client.get(f"/api/v1/analyses/{analysis_id}")
            assert get_response.json()["status"] == "COMPLETED"
    finally:
        app.dependency_overrides.clear()


def test_post_analyses_fails_cleanly_when_ai_provider_raises(db_session):
    provider = FakeAIProvider(extraction_exception=RuntimeError("simulated provider outage"))

    def override_get_db():
        yield db_session

    def override_get_service():
        yield AnalysisService(db_session, ai_provider=provider)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_analysis_service] = override_get_service
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/analyses", data={"text": SOURCE_TEXT})

            assert response.status_code == 201  # the request itself succeeds...
            body = response.json()
            assert body["status"] == "FAILED"  # ...but the analysis honestly reflects the failure
            assert body["error_code"] == "AI_EXTRACTION_FAILED"
            assert body["report_available"] is False
    finally:
        app.dependency_overrides.clear()
