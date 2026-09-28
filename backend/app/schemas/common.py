from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Stable machine-readable error code, e.g. UNSUPPORTED_FILE_TYPE.")
    message: str = Field(..., description="Human-readable description of the error.")
    details: dict[str, Any] | None = Field(default=None, description="Optional structured context (e.g. field errors).")
    request_id: str = Field(..., description="Correlation id for this request, echoed for support/debugging.")


class ErrorResponse(BaseModel):
    """The single error envelope returned by every failed API call.

    See docs/architecture/system-architecture.md ("Error Architecture")
    for the full error code catalogue and status code mapping.
    """

    error: ErrorDetail


class Pagination(BaseModel):
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total_items: int = Field(..., ge=0)
    total_pages: int = Field(..., ge=0)


class Page(BaseModel, Generic[T]):
    items: list[T]
    pagination: Pagination
