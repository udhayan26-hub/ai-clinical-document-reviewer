import uuid

from sqlalchemy import select

from app.models.processing_event import ProcessingEvent
from app.repositories.base import BaseRepository


class ProcessingEventRepository(BaseRepository[ProcessingEvent]):
    model = ProcessingEvent

    def create(self, event: ProcessingEvent) -> ProcessingEvent:
        return self.add(event)

    def list_for_analysis(self, analysis_id: uuid.UUID) -> list[ProcessingEvent]:
        stmt = (
            select(ProcessingEvent)
            .where(ProcessingEvent.analysis_id == analysis_id)
            .order_by(ProcessingEvent.created_at)
        )
        return list(self.db.execute(stmt).scalars().all())
