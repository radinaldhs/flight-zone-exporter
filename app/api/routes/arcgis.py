from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse

from app.models.schemas import (
    SPKDeleteRequest,
    SPKCheckResponse,
    SPKDeleteResponse,
    DashboardQueryResponse,
    SPKNumberQueryResponse
)
from app.models.user import UserInDB
from app.services.arcgis_service import ArcGISService
from app.core.dependencies import get_user_gis_credentials, get_current_active_user

router = APIRouter()


@router.get("/dashboard/regions", response_model=DashboardQueryResponse, tags=["Dashboard"])
async def get_regions(
    current_user: UserInDB = Depends(get_current_active_user),
    gis_credentials: dict = Depends(get_user_gis_credentials)
):
    arcgis_service = ArcGISService(gis_credentials)
    values = arcgis_service.get_regions(current_user.gis_auth_username)
    return {"values": values}


@router.get("/dashboard/districts", response_model=DashboardQueryResponse, tags=["Dashboard"])
async def get_districts(
    region: str = Query(...),
    current_user: UserInDB = Depends(get_current_active_user),
    gis_credentials: dict = Depends(get_user_gis_credentials)
):
    arcgis_service = ArcGISService(gis_credentials)
    values = arcgis_service.get_districts(current_user.gis_auth_username, region)
    return {"values": values}


@router.get("/dashboard/petaks", response_model=DashboardQueryResponse, tags=["Dashboard"])
async def get_petaks(
    district: str = Query(...),
    current_user: UserInDB = Depends(get_current_active_user),
    gis_credentials: dict = Depends(get_user_gis_credentials)
):
    arcgis_service = ArcGISService(gis_credentials)
    values = arcgis_service.get_petaks(current_user.gis_auth_username, district)
    return {"values": values}


@router.get("/dashboard/spk-numbers", response_model=SPKNumberQueryResponse, tags=["Dashboard"])
async def get_spk_numbers(
    petak: str = Query(...),
    current_user: UserInDB = Depends(get_current_active_user),
    gis_credentials: dict = Depends(get_user_gis_credentials)
):
    arcgis_service = ArcGISService(gis_credentials)
    values = arcgis_service.get_spk_numbers(current_user.gis_auth_username, petak)
    return {"values": values}


@router.post("/spk/check", response_model=SPKCheckResponse, tags=["ArcGIS"])
async def check_spk(
    request: SPKDeleteRequest,
    gis_credentials: dict = Depends(get_user_gis_credentials)
):
    arcgis_service = ArcGISService(gis_credentials)
    result = arcgis_service.check_spk_exists(request.spk_number)
    return result


@router.delete("/spk", response_model=SPKDeleteResponse, tags=["ArcGIS"])
async def delete_spk(
    request: SPKDeleteRequest,
    gis_credentials: dict = Depends(get_user_gis_credentials)
):
    arcgis_service = ArcGISService(gis_credentials)
    result = arcgis_service.delete_spk(request.spk_number)
    return result
