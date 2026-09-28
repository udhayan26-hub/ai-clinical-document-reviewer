import uuid

from app.models.document import Document
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    model = Document

    def create(self, document: Document) -> Document:
        return self.add(document)

    def get(self, document_id: uuid.UUID) -> Document | None:
        return self.db.get(Document, document_id)
