"""Analysis orchestration service.

Owns: input validation, the create/read use cases for analyses, and (once
implemented) driving an analysis through its processing lifecycle by
calling `app.document_processing` and `app.ai` interfaces in sequence and
persisting the result via `app.repositories`.

Does NOT own: HTTP concerns (status codes, request parsing — that's
`app.api`), SQL (that's `app.repositories`), or how text is actually
extracted/analyzed (that's `app.document_processing` / `app.ai`
implementations, not yet written).

`run_pipeline` is the seam where the real document-processing and AI/ML
work will be wired in; it is intentionally unimplemented in this phase.
"""

import hashlib
import uuid

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import AnalysisStatus, DocumentSourceType, ProcessingEventType
from app.core.exceptions import (
    EmptyInputError,
    FileTooLargeError,
    ResourceNotFoundError,
    ReportNotReadyError,
    UnsupportedFileTypeError,
    ValidationFailedError,
)
from app.models.analysis import Analysis
from app.models.clinical_report import ClinicalReport
from app.models.document import Document
from app.models.processing_event import ProcessingEvent
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.clinical_report_repository import ClinicalReportRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.processing_event_repository import ProcessingEventRepository

SUPPORTED_FILE_CONTENT_TYPES: dict[str, DocumentSourceType] = {
    "application/pdf": DocumentSourceType.PDF,
    "image/png": DocumentSourceType.IMAGE,
    "image/jpeg": DocumentSourceType.IMAGE,
    "image/jpg": DocumentSourceType.IMAGE,
    "image/tiff": DocumentSourceType.IMAGE,
    "image/bmp": DocumentSourceType.IMAGE,
    "image/webp": DocumentSourceType.IMAGE,
}


class AnalysisService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.documents = DocumentRepository(db)
        self.analyses = AnalysisRepository(db)
        self.reports = ClinicalReportRepository(db)
        self.events = ProcessingEventRepository(db)
        self.settings = get_settings()

    # ---- Use cases ------------------------------------------------------

    def create_analysis(
        self,
        *,
        text: str | None,
        filename: str | None,
        content_type: str | None,
        file_bytes: bytes | None,
    ) -> Analysis:
        self._validate_exactly_one_input(text, file_bytes)

        if text is not None:
            if not text.strip():
                raise EmptyInputError("Submitted text content is empty.")
            source_type = DocumentSourceType.TEXT
            resolved_content_type = "text/plain"
            raw_bytes = text.encode("utf-8")
        else:
            assert file_bytes is not None  # guaranteed by _validate_exactly_one_input
            if not file_bytes:
                raise EmptyInputError("Submitted file is empty.")
            source_type = self._resolve_source_type(content_type)
            self._validate_size(len(file_bytes))
            raw_bytes = file_bytes

        checksum = hashlib.sha256(raw_bytes).hexdigest()

        document = Document(
            source_type=source_type,
            original_filename=filename,
            content_type=(content_type or "text/plain").lower(),
            size_bytes=len(raw_bytes),
            checksum_sha256=checksum,
            storage_uri=None,  # object storage persistence is not yet implemented
        )
        self.documents.create(document)

        analysis = Analysis(
            document=document,
            status=AnalysisStatus.PENDING,
            extracted_text=text if source_type == DocumentSourceType.TEXT else None,
        )
        self.analyses.create(analysis)

        self.events.create(
            ProcessingEvent(
                analysis=analysis,
                event_type=ProcessingEventType.STATUS_CHANGED,
                message="Analysis created and queued for processing.",
                event_metadata={"status": AnalysisStatus.PENDING.value},
            )
        )

        self.db.commit()
        self.db.refresh(analysis)
        return analysis

    def get_analysis(self, analysis_id: uuid.UUID) -> Analysis:
        analysis = self.analyses.get(analysis_id)
        if analysis is None:
            raise ResourceNotFoundError(f"Analysis '{analysis_id}' was not found.")
        return analysis

    def list_analyses(
        self, *, status: AnalysisStatus | None, page: int, page_size: int
    ) -> tuple[list[Analysis], int]:
        return self.analyses.list(status=status, page=page, page_size=page_size)

    def get_report(self, analysis_id: uuid.UUID) -> ClinicalReport:
        analysis = self.get_analysis(analysis_id)
        if analysis.status != AnalysisStatus.COMPLETED:
            raise ReportNotReadyError(
                f"Analysis '{analysis_id}' has status {analysis.status.value}; "
                "a report is only available once status is COMPLETED."
            )
        report = self.reports.get_by_analysis_id(analysis_id)
        if report is None:
            # Should not happen if COMPLETED is only ever set alongside report
            # persistence (see run_pipeline), but guard defensively.
            raise ResourceNotFoundError(f"No report found for completed analysis '{analysis_id}'.")
        return report

    def run_pipeline(self, analysis_id: uuid.UUID) -> None:
        """Drive one analysis through VALIDATING -> EXTRACTING -> ANALYZING
        -> COMPLETED/FAILED by calling `app.document_processing` and
        `app.ai` interfaces, recording a ProcessingEvent at each
        transition. Intentionally not implemented in this phase — see
        docs/architecture/system-architecture.md, "Processing Lifecycle".
        """
        raise NotImplementedError(
            "Pipeline execution is not implemented yet; analyses currently remain PENDING."
        )

    # ---- Validation helpers ----------------------------------------------

    @staticmethod
    def _validate_exactly_one_input(text: str | None, file_bytes: bytes | None) -> None:
        provided = [value is not None for value in (text, file_bytes)]
        if not any(provided):
            raise EmptyInputError("Either 'text' or a 'file' upload must be provided.")
        if all(provided):
            raise ValidationFailedError("Provide either 'text' or a 'file' upload, not both.")

    @staticmethod
    def _resolve_source_type(content_type: str | None) -> DocumentSourceType:
        normalized = (content_type or "").lower()
        source_type = SUPPORTED_FILE_CONTENT_TYPES.get(normalized)
        if source_type is None:
            raise UnsupportedFileTypeError(
                f"Content type '{content_type}' is not supported. "
                f"Supported types: {sorted(SUPPORTED_FILE_CONTENT_TYPES)}."
            )
        return source_type

    def _validate_size(self, size_bytes: int) -> None:
        if size_bytes > self.settings.upload_max_size_bytes:
            raise FileTooLargeError(
                f"File size {size_bytes} bytes exceeds the maximum of "
                f"{self.settings.upload_max_size_bytes} bytes."
            )
