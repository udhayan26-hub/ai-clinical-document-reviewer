from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.analysis_service import AnalysisService


def get_analysis_service(db: Session = Depends(get_db)) -> Generator[AnalysisService, None, None]:
    yield AnalysisService(db)
