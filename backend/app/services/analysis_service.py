"""Analysis orchestration service.

Owns: input validation, the create/read use cases for analyses, and
driving an analysis through its processing lifecycle by calling
`app.document_processing` and `app.ai` interfaces in sequence and
persisting the result via `app.repositories`.

Does NOT own: HTTP concerns (status codes, request parsing — that's
`app.api`), SQL (that's `app.repositories`), how text is actually
extracted (that's `app.document_processing` implementations), or how
clinical analysis is actually performed (that's `app.ai.pipeline` and
the configured `AIProvider`/`ClinicalReportValidator`).

`run_pipeline` is the seam where document-processing and the AI/ML
pipeline are wired in. `POST /api/v1/analyses` now calls it synchronously
after `create_analysis` — there is no background job queue yet, so that
request blocks on document processing + the AI provider call (see
docs/decisions/008-ai-pipeline.md "What Async Will Need"). It never
raises: any failure is reflected as `Analysis.status == FAILED`.
"""

import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.ai.factory import get_default_ai_provider, get_default_validator
from app.ai.interfaces import AIProvider, ClinicalReportValidator
from app.ai.pipeline import ClinicalAnalysisPipeline
from app.ai.schemas import PipelineResult
from app.core.config import get_settings
from app.core.enums import ANALYSIS_STATUS_TRANSITIONS, AnalysisStatus, DocumentSourceType, ProcessingEventType
from app.core.exceptions import (
    AppError,
    DocumentBytesUnavailableError,
    EmptyInputError,
    FileTooLargeError,
    ResourceNotFoundError,
    ReportNotReadyError,
    UnsupportedFileTypeError,
    ValidationFailedError,
)
from app.document_processing.factory import get_processor
from app.document_processing.interfaces import NormalizedDocument
from app.document_processing.text_processor import TextProcessor
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
    def __init__(
        self,
        db: Session,
        *,
        ai_provider: AIProvider | None = None,
        ai_validator: ClinicalReportValidator | None = None,
    ) -> None:
        self.db = db
        self.documents = DocumentRepository(db)
        self.analyses = AnalysisRepository(db)
        self.reports = ClinicalReportRepository(db)
        self.events = ProcessingEventRepository(db)
        self.settings = get_settings()
        # Overridable so tests can inject a deterministic FakeAIProvider
        # without going through app.ai.factory's real-config-driven default.
        # Resolved lazily (in run_pipeline, not here) so a misconfigured
        # AI_PROVIDER only breaks analysis *processing* — never unrelated
        # calls like get_analysis/list_analyses, which don't need it.
        self._ai_provider_override = ai_provider
        self._ai_validator_override = ai_validator

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
        storage_uri = self._persist_file_bytes(checksum, raw_bytes) if source_type != DocumentSourceType.TEXT else None

        document = Document(
            source_type=source_type,
            original_filename=filename,
            content_type=(content_type or "text/plain").lower(),
            size_bytes=len(raw_bytes),
            checksum_sha256=checksum,
            storage_uri=storage_uri,
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

    def run_pipeline(self, analysis_id: uuid.UUID) -> Analysis:
        """Drive one analysis through VALIDATING -> EXTRACTING -> ANALYZING
        -> COMPLETED/FAILED, recording a ProcessingEvent at every
        transition. Never raises: any failure at any stage is caught and
        recorded as AnalysisStatus.FAILED with a safe error_code/message —
        callers should inspect the returned Analysis, not a try/except.

        Called synchronously from `POST /api/v1/analyses` (see
        `app.api.v1.analyses.create_analysis`) — there is no background
        job queue, so the request blocks on this. Also callable directly
        (e.g. from a script or a test).
        """
        analysis = self.get_analysis(analysis_id)
        try:
            # Resolved here, not in __init__, so a misconfigured AI_PROVIDER
            # only fails analysis *processing* — get_analysis/list_analyses
            # never touch this and are unaffected.
            provider = self._ai_provider_override or get_default_ai_provider()
            validator = self._ai_validator_override or get_default_validator()

            self._transition(analysis, AnalysisStatus.VALIDATING, ProcessingEventType.STATUS_CHANGED, "Validating document for processing.")

            self._transition(
                analysis, AnalysisStatus.EXTRACTING, ProcessingEventType.EXTRACTION_STARTED, "Extracting normalized text from document."
            )
            normalized = self._build_normalized_document(analysis)
            self._record_event(
                analysis,
                ProcessingEventType.EXTRACTION_COMPLETED,
                "Document text extraction completed.",
                {"document_type": normalized.document_type.value, "requires_ocr": str(normalized.requires_ocr)},
            )

            self._transition(
                analysis,
                AnalysisStatus.ANALYZING,
                ProcessingEventType.AI_ANALYSIS_STARTED,
                "Running AI/ML clinical analysis pipeline.",
                {"provider": type(provider).__name__},
            )
            pipeline = ClinicalAnalysisPipeline(provider, validator)
            result = pipeline.run(normalized)

            self._persist_report(analysis, result)
            self._record_event(
                analysis,
                ProcessingEventType.AI_ANALYSIS_COMPLETED,
                "AI/ML clinical analysis completed.",
                {"fact_count": str(len(result.extraction.facts)), "issue_count": str(len(result.validation.issues))},
            )
            self._record_event(analysis, ProcessingEventType.REPORT_PERSISTED, "Clinical report persisted.")

            self._transition(analysis, AnalysisStatus.COMPLETED, ProcessingEventType.STATUS_CHANGED, "Analysis completed.")
        except AppError as exc:
            self._fail(analysis, exc)
        except Exception:
            # Never let an unexpected internal exception escape this method
            # or leak its details into persisted state — see
            # docs/architecture/system-architecture.md "Error Architecture".
            self._fail(analysis, AppError("An unexpected internal error occurred."))

        return analysis

    def _persist_file_bytes(self, checksum: str, raw_bytes: bytes) -> str:
        """Writes uploaded file bytes to local disk, keyed by content
        checksum (see docs/decisions/005-storage.md: local filesystem for
        dev, same `storage_uri` contract would point at S3 later). Reusing
        the checksum as the filename means re-uploading identical content
        is naturally deduplicated on disk.
        """
        storage_dir = Path(self.settings.upload_storage_dir)
        storage_dir.mkdir(parents=True, exist_ok=True)
        path = storage_dir / checksum
        path.write_bytes(raw_bytes)
        return str(path)

    def _build_normalized_document(self, analysis: Analysis) -> NormalizedDocument:
        document = analysis.document
        if document.source_type == DocumentSourceType.TEXT:
            if not analysis.extracted_text:
                raise DocumentBytesUnavailableError("No text content is stored for this analysis.")
            return TextProcessor().process(analysis.extracted_text.encode("utf-8"))
        if not document.storage_uri:
            raise DocumentBytesUnavailableError(
                f"Raw {document.source_type.value} file bytes were not persisted at upload time."
            )
        raw_bytes = Path(document.storage_uri).read_bytes()
        return get_processor(document.source_type).process(raw_bytes)

    def _persist_report(self, analysis: Analysis, result: PipelineResult) -> None:
        validated_report = result.validation.report
        assert validated_report is not None  # guaranteed: PipelineResult is only returned when VALID
        self.reports.create(
            ClinicalReport(
                analysis=analysis,
                structured_data=validated_report.model_dump(mode="json"),
                report_summary=validated_report.report_summary,
                requires_review=validated_report.requires_review,
                ai_provider=self.settings.ai_provider,
                ai_model_name=self.settings.ai_model_name,
                generated_at=datetime.now(timezone.utc),
            )
        )
        self.db.commit()

    def _transition(
        self,
        analysis: Analysis,
        new_status: AnalysisStatus,
        event_type: ProcessingEventType,
        message: str,
        metadata: dict[str, str] | None = None,
    ) -> None:
        if new_status not in ANALYSIS_STATUS_TRANSITIONS[analysis.status]:
            raise AppError(f"Illegal status transition from {analysis.status.value} to {new_status.value}.")
        if analysis.started_at is None and new_status == AnalysisStatus.VALIDATING:
            analysis.started_at = datetime.now(timezone.utc)
        if new_status == AnalysisStatus.COMPLETED:
            analysis.completed_at = datetime.now(timezone.utc)
        analysis.status = new_status
        self._record_event(analysis, event_type, message, metadata)

    def _record_event(
        self, analysis: Analysis, event_type: ProcessingEventType, message: str, metadata: dict[str, str] | None = None
    ) -> None:
        self.events.create(
            ProcessingEvent(analysis=analysis, event_type=event_type, message=message, event_metadata=metadata)
        )
        self.db.commit()

    def _fail(self, analysis: Analysis, exc: AppError) -> None:
        event_type = {
            AnalysisStatus.VALIDATING: ProcessingEventType.VALIDATION_FAILED,
            AnalysisStatus.EXTRACTING: ProcessingEventType.EXTRACTION_FAILED,
            AnalysisStatus.ANALYZING: ProcessingEventType.AI_ANALYSIS_FAILED,
        }.get(analysis.status, ProcessingEventType.ERROR)
        analysis.status = AnalysisStatus.FAILED
        analysis.error_code = exc.code
        analysis.error_message = exc.message
        analysis.completed_at = datetime.now(timezone.utc)
        self._record_event(analysis, event_type, exc.message, {"error_code": exc.code})

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
