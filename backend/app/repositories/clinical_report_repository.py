import uuid

from sqlalchemy import select

from app.models.clinical_report import ClinicalReport
from app.repositories.base import BaseRepository


class ClinicalReportRepository(BaseRepository[ClinicalReport]):
    model = ClinicalReport

    def create(self, report: ClinicalReport) -> ClinicalReport:
        return self.add(report)

    def get_by_analysis_id(self, analysis_id: uuid.UUID) -> ClinicalReport | None:
        stmt = select(ClinicalReport).where(ClinicalReport.analysis_id == analysis_id)
        return self.db.execute(stmt).scalar_one_or_none()
