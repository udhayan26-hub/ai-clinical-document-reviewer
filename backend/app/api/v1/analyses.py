import math
import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status

from app.api.deps import get_analysis_service
from app.core.enums import AnalysisStatus
from app.models.analysis import Analysis
from app.schemas.analysis import AnalysisResponse
from app.schemas.clinical_report import ClinicalReport, ClinicalReportResponse
from app.schemas.common import ErrorResponse, Page, Pagination
from app.schemas.document import DocumentSummary
from app.services.analysis_service import AnalysisService

router = APIRouter(prefix="/api/v1/analyses", tags=["analyses"])

COMMON_ERROR_RESPONSES: dict[int | str, dict] = {
    400: {"model": ErrorResponse, "description": "Validation failed / empty input."},
    404: {"model": ErrorResponse, "description": "Resource not found."},
    413: {"model": ErrorResponse, "description": "File too large."},
    415: {"model": ErrorResponse, "description": "Unsupported file type."},
    422: {"model": ErrorResponse, "description": "File corrupted or unprocessable."},
    500: {"model": ErrorResponse, "description": "Internal server error."},
}


def _to_response(analysis: Analysis) -> AnalysisResponse:
    return AnalysisResponse(
        id=analysis.id,
        status=analysis.status,
        document=DocumentSummary.model_validate(analysis.document),
        error_code=analysis.error_code,
        error_message=analysis.error_message,
        report_available=analysis.status == AnalysisStatus.COMPLETED,
        created_at=analysis.created_at,
        updated_at=analysis.updated_at,
        started_at=analysis.started_at,
        completed_at=analysis.completed_at,
    )


@router.post(
    "",
    response_model=AnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    responses=COMMON_ERROR_RESPONSES,
    summary="Submit a clinical document for analysis",
)
async def create_analysis(
    text: str | None = Form(default=None, description="Plain-text clinical document content."),
    file: UploadFile | None = File(default=None, description="Image (scanned/handwritten) or PDF document."),
    service: AnalysisService = Depends(get_analysis_service),
) -> AnalysisResponse:
    """Submit exactly one of `text` or `file`. Returns immediately with
    status PENDING — this endpoint only validates and persists the
    submission; running it through the processing pipeline is not yet
    implemented (see `AnalysisService.run_pipeline`).
    """
    file_bytes = await file.read() if file is not None else None
    analysis = service.create_analysis(
        text=text,
        filename=file.filename if file is not None else None,
        content_type=file.content_type if file is not None else None,
        file_bytes=file_bytes,
    )
    return _to_response(analysis)


@router.get(
    "",
    response_model=Page[AnalysisResponse],
    responses=COMMON_ERROR_RESPONSES,
    summary="List submitted analyses",
)
def list_analyses(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: AnalysisStatus | None = Query(default=None, alias="status"),
    service: AnalysisService = Depends(get_analysis_service),
) -> Page[AnalysisResponse]:
    items, total = service.list_analyses(status=status_filter, page=page, page_size=page_size)
    total_pages = math.ceil(total / page_size) if total else 0
    return Page[AnalysisResponse](
        items=[_to_response(item) for item in items],
        pagination=Pagination(page=page, page_size=page_size, total_items=total, total_pages=total_pages),
    )


@router.get(
    "/{analysis_id}",
    response_model=AnalysisResponse,
    responses=COMMON_ERROR_RESPONSES,
    summary="Get analysis status and metadata",
)
def get_analysis(
    analysis_id: uuid.UUID,
    service: AnalysisService = Depends(get_analysis_service),
) -> AnalysisResponse:
    analysis = service.get_analysis(analysis_id)
    return _to_response(analysis)


@router.get(
    "/{analysis_id}/report",
    response_model=ClinicalReportResponse,
    responses={**COMMON_ERROR_RESPONSES, 409: {"model": ErrorResponse, "description": "Report not ready."}},
    summary="Get the structured clinical report for a completed analysis",
)
def get_analysis_report(
    analysis_id: uuid.UUID,
    service: AnalysisService = Depends(get_analysis_service),
) -> ClinicalReportResponse:
    report_row = service.get_report(analysis_id)
    return ClinicalReportResponse(
        analysis_id=report_row.analysis_id,
        report=ClinicalReport(**report_row.structured_data),
        ai_provider=report_row.ai_provider,
        ai_model_name=report_row.ai_model_name,
        generated_at=report_row.generated_at,
    )
