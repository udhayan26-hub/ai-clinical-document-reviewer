import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import AnalysisStatus
from app.schemas.document import DocumentSummary


class AnalysisResponse(BaseModel):
    """Response body for analysis creation, retrieval, and list items.

    POST /api/v1/analyses is multipart/form-data (exactly one of `text` or
    `file` fields), not a JSON body, so there is no corresponding
    "AnalysisCreateRequest" schema — see docs/architecture/system-architecture.md
    for the full request contract.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: AnalysisStatus
    document: DocumentSummary
    error_code: str | None = None
    error_message: str | None = None
    report_available: bool = Field(..., description="True once status == COMPLETED and a report exists.")
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class AnalysisListQuery(BaseModel):
    """Query parameters accepted by GET /api/v1/analyses."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    status: AnalysisStatus | None = Field(default=None, description="Filter by processing status.")
