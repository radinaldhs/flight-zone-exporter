from fastapi import APIRouter

from app.core.config import settings
from app.models.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "app_name": settings.APP_NAME
    }
