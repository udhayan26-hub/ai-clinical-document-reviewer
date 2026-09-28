"""Application error taxonomy.

Every error the API can return to a client is represented by an `AppError`
subclass here. Each carries a stable machine-readable `code`, an HTTP
`status_code`, and a human-readable `message`. `app.core.error_handlers`
converts any `AppError` into the standard error response envelope
documented in docs/architecture/system-architecture.md ("Error
Architecture").

Business logic (services/, document_processing/, ai/, repositories/)
should raise these instead of returning ad-hoc error dicts or leaking
framework/library-specific exceptions (e.g. SQLAlchemy, PyPDF, provider
SDK errors) past its own boundary.
"""

from typing import Any


class AppError(Exception):
    code: str = "INTERNAL_ERROR"
    status_code: int = 500
    message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None, *, details: dict[str, Any] | None = None) -> None:
        self.message = message or self.message
        self.details = details
        super().__init__(self.message)


# ---- Input / validation errors (4xx) ----------------------------------


class EmptyInputError(AppError):
    code = "EMPTY_INPUT"
    status_code = 400
    message = "No document content was provided."


class ValidationFailedError(AppError):
    code = "VALIDATION_FAILED"
    status_code = 400
    message = "The submitted request failed validation."


class UnsupportedFileTypeError(AppError):
    code = "UNSUPPORTED_FILE_TYPE"
    status_code = 415
    message = "The submitted file type is not supported."


class FileTooLargeError(AppError):
    code = "FILE_TOO_LARGE"
    status_code = 413
    message = "The submitted file exceeds the maximum allowed size."


class CorruptedFileError(AppError):
    code = "CORRUPTED_FILE"
    status_code = 422
    message = "The submitted file could not be read; it may be corrupted."


class ResourceNotFoundError(AppError):
    code = "NOT_FOUND"
    status_code = 404
    message = "The requested resource was not found."


class ReportNotReadyError(AppError):
    code = "REPORT_NOT_READY"
    status_code = 409
    message = "The clinical report is not yet available for this analysis."


# ---- Document processing errors (422 — request was valid, processing failed) --


class TextExtractionError(AppError):
    code = "EXTRACTION_FAILED"
    status_code = 422
    message = "Failed to extract text from the submitted document."


class OCRFailedError(AppError):
    code = "OCR_FAILED"
    status_code = 422
    message = "Failed to extract text from the submitted image via OCR."


# ---- AI/ML pipeline errors ----------------------------------------------


class AIProcessingError(AppError):
    code = "AI_PROCESSING_FAILED"
    status_code = 502
    message = "The AI/ML clinical analysis step failed."


class MalformedStructuredOutputError(AppError):
    code = "MALFORMED_AI_OUTPUT"
    status_code = 502
    message = "The AI/ML pipeline returned output that does not conform to the expected report schema."


# ---- Infrastructure errors ----------------------------------------------


class PersistenceError(AppError):
    code = "PERSISTENCE_FAILED"
    status_code = 500
    message = "Failed to persist data."


class ExternalServiceError(AppError):
    code = "EXTERNAL_SERVICE_FAILED"
    status_code = 503
    message = "A required external service is unavailable or returned an error."
