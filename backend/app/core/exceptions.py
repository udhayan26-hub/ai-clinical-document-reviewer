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


class DocumentBytesUnavailableError(AppError):
    """Raised when re-processing a document requires its raw bytes and
    they were never persisted — currently true for every PDF/IMAGE
    analysis, since object storage writes are not yet implemented (see
    docs/decisions/005-storage.md). TEXT analyses are unaffected: their
    content is already stored as `Analysis.extracted_text`.
    """

    code = "DOCUMENT_BYTES_UNAVAILABLE"
    status_code = 422
    message = "The original document bytes are not available for processing."


# ---- AI/ML pipeline errors ----------------------------------------------


class AIProcessingError(AppError):
    """Base class for any AI-provider-level failure. Callers that don't
    care which stage failed can catch this; the pipeline orchestrator
    always raises one of the two specific subclasses below instead of
    this directly.
    """

    code = "AI_PROCESSING_FAILED"
    status_code = 502
    message = "The AI/ML clinical analysis step failed."


class AIExtractionFailedError(AIProcessingError):
    code = "AI_EXTRACTION_FAILED"
    message = "The AI provider failed while extracting structured clinical facts."


class AIGenerationFailedError(AIProcessingError):
    code = "AI_GENERATION_FAILED"
    message = "The AI provider failed while generating the draft clinical report."


class EvidenceMismatchError(AppError):
    code = "EVIDENCE_MISMATCH"
    status_code = 422
    message = "Extracted facts cite evidence that could not be found in the source document."


class ReportValidationFailedError(AppError):
    code = "REPORT_VALIDATION_FAILED"
    status_code = 422
    message = "The generated clinical report failed deterministic validation."


class UnsupportedAIProviderError(AppError):
    code = "UNSUPPORTED_AI_PROVIDER"
    status_code = 501
    message = "No usable AI provider is configured."


# ---- Infrastructure errors ----------------------------------------------


class PersistenceError(AppError):
    code = "PERSISTENCE_FAILED"
    status_code = 500
    message = "Failed to persist data."


class ExternalServiceError(AppError):
    code = "EXTERNAL_SERVICE_FAILED"
    status_code = 503
    message = "A required external service is unavailable or returned an error."
