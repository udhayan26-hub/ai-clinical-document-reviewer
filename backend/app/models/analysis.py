import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import AnalysisStatus
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Analysis(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A single request to process one Document through the pipeline.

    Owns: processing status/lifecycle timestamps and the normalized text
    once extracted. Does not own the structured clinical findings (see
    `ClinicalReport`) or the raw source bytes (see `Document`).
    """

    __tablename__ = "analyses"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[AnalysisStatus] = mapped_column(
        SAEnum(AnalysisStatus, name="analysis_status", native_enum=False, validate_strings=True),
        nullable=False,
        default=AnalysisStatus.PENDING,
    )
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Normalized plain text produced by the document-processing stage
    # (direct pass-through for TEXT, extracted for PDF, OCR output for IMAGE).
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    document: Mapped["Document"] = relationship(back_populates="analyses")
    clinical_report: Mapped["ClinicalReport | None"] = relationship(
        back_populates="analysis", uselist=False, cascade="all, delete-orphan"
    )
    processing_events: Mapped[list["ProcessingEvent"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan", order_by="ProcessingEvent.created_at"
    )

    __table_args__ = (
        Index("ix_analyses_document_id", "document_id"),
        Index("ix_analyses_status", "status"),
        Index("ix_analyses_created_at", "created_at"),
    )
