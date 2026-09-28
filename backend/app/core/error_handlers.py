import logging
import uuid

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppError
from app.schemas.common import ErrorDetail, ErrorResponse

logger = logging.getLogger("app.errors")


def _request_id(request: Request) -> str:
    existing = request.headers.get("x-request-id")
    return existing or str(uuid.uuid4())


def _envelope(code: str, message: str, request_id: str, details: dict | None = None) -> dict:
    return ErrorResponse(
        error=ErrorDetail(code=code, message=message, details=details, request_id=request_id)
    ).model_dump()


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        request_id = _request_id(request)
        if exc.status_code >= 500:
            logger.exception("Unhandled application error [%s] %s", exc.code, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(exc.code, exc.message, request_id, exc.details),
            headers={"x-request-id": request_id},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = _request_id(request)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_envelope(
                "VALIDATION_FAILED",
                "The submitted request failed validation.",
                request_id,
                {"errors": exc.errors()},
            ),
            headers={"x-request-id": request_id},
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        request_id = _request_id(request)
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope("HTTP_ERROR", str(exc.detail), request_id),
            headers={"x-request-id": request_id},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        request_id = _request_id(request)
        logger.exception("Unhandled exception (request_id=%s)", request_id)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_envelope("INTERNAL_ERROR", "An unexpected error occurred.", request_id),
            headers={"x-request-id": request_id},
        )
