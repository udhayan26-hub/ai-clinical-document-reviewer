import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import DocumentSourceType


class DocumentSummary(BaseModel):
    """Read-only summary of the submitted source document, embedded in
    AnalysisResponse. Never exposes storage_uri (internal implementation
    detail of the storage backend).
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_type: DocumentSourceType
    original_filename: str | None
    content_type: str | None
    size_bytes: int
    created_at: datetime
