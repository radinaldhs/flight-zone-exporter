from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from app.models.schemas import (
    SPKDeleteRequest,
    SPKCheckResponse,
    SPKDeleteResponse
)
from app.services.arcgis_service import ArcGISService
from app.core.dependencies import get_user_gis_credentials

router = APIRouter()


@router.post("/spk/check", response_model=SPKCheckResponse, tags=["ArcGIS"])
async def check_spk(
    request: SPKDeleteRequest,
    gis_credentials: dict = Depends(get_user_gis_credentials)
):
    """Check if SPK exists in ArcGIS (requires authentication)"""
    arcgis_service = ArcGISService(gis_credentials)
    result = arcgis_service.check_spk_exists(request.spk_number)
    return result


@router.delete("/spk", response_model=SPKDeleteResponse, tags=["ArcGIS"])
async def delete_spk(
    request: SPKDeleteRequest,
    gis_credentials: dict = Depends(get_user_gis_credentials)
):
    """Delete SPK data from ArcGIS (requires authentication)"""
    arcgis_service = ArcGISService(gis_credentials)
    result = arcgis_service.delete_spk(request.spk_number)
    return result
