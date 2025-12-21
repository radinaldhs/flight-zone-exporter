from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.models.schemas import (
    SPKDeleteRequest,
    SPKCheckResponse,
    SPKDeleteResponse
)
from app.services.arcgis_service import ArcGISService

router = APIRouter()


@router.post("/spk/check", response_model=SPKCheckResponse, tags=["ArcGIS"])
async def check_spk(request: SPKDeleteRequest):
    arcgis_service = ArcGISService()
    result = arcgis_service.check_spk_exists(request.spk_number)
    return result


@router.delete("/spk", response_model=SPKDeleteResponse, tags=["ArcGIS"])
async def delete_spk(request: SPKDeleteRequest):
    arcgis_service = ArcGISService()
    result = arcgis_service.delete_spk(request.spk_number)
    return result
