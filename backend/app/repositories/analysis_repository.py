import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.core.enums import AnalysisStatus
from app.models.analysis import Analysis
from app.repositories.base import BaseRepository


class AnalysisRepository(BaseRepository[Analysis]):
    model = Analysis

    def create(self, analysis: Analysis) -> Analysis:
        return self.add(analysis)

    def get(self, analysis_id: uuid.UUID) -> Analysis | None:
        stmt = (
            select(Analysis)
            .options(joinedload(Analysis.document), joinedload(Analysis.clinical_report))
            .where(Analysis.id == analysis_id)
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def list(
        self, *, status: AnalysisStatus | None, page: int, page_size: int
    ) -> tuple[list[Analysis], int]:
        base_stmt = select(Analysis)
        count_stmt = select(func.count()).select_from(Analysis)
        if status is not None:
            base_stmt = base_stmt.where(Analysis.status == status)
            count_stmt = count_stmt.where(Analysis.status == status)

        total = self.db.execute(count_stmt).scalar_one()

        stmt = (
            base_stmt.options(joinedload(Analysis.document))
            .order_by(Analysis.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list(self.db.execute(stmt).unique().scalars().all())
        return items, total
