from fastapi import APIRouter

from app.api.v1.analyses import router as analyses_router

api_v1_router = APIRouter()
api_v1_router.include_router(analyses_router)

__all__ = ["api_v1_router"]
