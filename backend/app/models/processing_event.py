import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ProcessingEventType
from app.models.base import Base, UUIDPrimaryKeyMixin

PortableJSON = JSON().with_variant(JSONB(), "postgresql")


class ProcessingEvent(Base, UUIDPrimaryKeyMixin):
    """Append-only audit log entry for one Analysis.

    Owns: the historical record of what happened and when (for debugging,
    support, and displaying processing progress). Never updated or
    deleted except via cascade when its Analysis is deleted. Does not own
    current status (see `Analysis.status`, which is the source of truth
    for "where things are now").
    """

    __tablename__ = "processing_events"

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[ProcessingEventType] = mapped_column(
        SAEnum(ProcessingEventType, name="processing_event_type", native_enum=False, validate_strings=True),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    event_metadata: Mapped[dict[str, Any] | None] = mapped_column(PortableJSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    analysis: Mapped["Analysis"] = relationship(back_populates="processing_events")

    __table_args__ = (
        Index("ix_processing_events_analysis_id", "analysis_id"),
        Index("ix_processing_events_created_at", "created_at"),
    )
