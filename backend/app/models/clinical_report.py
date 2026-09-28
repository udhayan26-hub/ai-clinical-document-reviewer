import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

# Portable JSON type: renders as native JSONB on PostgreSQL, falls back to
# generic JSON (TEXT-backed) on other dialects such as SQLite in tests.
PortableJSON = JSON().with_variant(JSONB(), "postgresql")


class ClinicalReport(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """The structured clinical output produced by the AI/ML pipeline for
    exactly one Analysis (1:1).

    Owns: the structured report payload and provenance of how it was
    generated. Does not own processing status (see `Analysis`) or the
    audit trail of how it got there (see `ProcessingEvent`).

    `structured_data` stores the nested sections of the report contract
    defined in `app.schemas.clinical_report.ClinicalReport` (symptoms,
    diagnoses, medications, vitals, allergies, observations, concerns,
    missing_information, potential_inconsistencies) as JSONB, since their
    shape is rich/nested and evolves with the AI pipeline rather than the
    relational schema.
    """

    __tablename__ = "clinical_reports"

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    # Full serialized app.schemas.clinical_report.ClinicalReport payload
    # (i.e. report.model_dump()) — the single source of truth for
    # reconstructing the report. report_summary/requires_review below are
    # promoted copies of the same-named fields, kept only so they can be
    # indexed/filtered/displayed without deserializing the JSONB blob.
    structured_data: Mapped[dict[str, Any]] = mapped_column(PortableJSON, nullable=False)
    report_summary: Mapped[str] = mapped_column(Text, nullable=False)
    requires_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    ai_provider: Mapped[str] = mapped_column(String(128), nullable=False)
    ai_model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    analysis: Mapped["Analysis"] = relationship(back_populates="clinical_report")
