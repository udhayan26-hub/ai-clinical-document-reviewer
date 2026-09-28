from sqlalchemy import Enum as SAEnum
from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import DocumentSourceType
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Document(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A single uploaded/submitted source artifact (raw text, image, or PDF).

    Owns: the immutable record of *what was submitted* and where its bytes
    live. Does not own analysis status, extracted text, or AI results —
    those belong to `Analysis` and `ClinicalReport`.
    """

    __tablename__ = "documents"

    source_type: Mapped[DocumentSourceType] = mapped_column(
        SAEnum(DocumentSourceType, name="document_source_type", native_enum=False, validate_strings=True),
        nullable=False,
    )
    original_filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    # For TEXT submissions, storage_uri may be null and the content lives
    # only as extracted_text on the related Analysis; for IMAGE/PDF it
    # points at the object storage location (local disk in dev, S3 later).
    storage_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    analyses: Mapped[list["Analysis"]] = relationship(back_populates="document")

    __table_args__ = (
        Index("ix_documents_checksum_sha256", "checksum_sha256"),
    )
