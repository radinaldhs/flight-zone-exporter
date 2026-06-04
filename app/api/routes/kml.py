import math
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from starlette.background import BackgroundTask

from app.core.dependencies import get_user_gis_credentials
from app.core.exceptions import InvalidFileFormatError
from app.services.arcgis_service import ArcGISService
from app.services.kml_parser import KMLParser
from app.services.shapefile_service import ShapefileService
from app.utils.file_utils import FileUtils

router = APIRouter()


def _validate_positive(name: str, value: Optional[float]) -> None:
    if value is not None and (not math.isfinite(value) or value <= 0):
        raise HTTPException(status_code=422, detail=f"Invalid {name}: must be a positive number")


@router.post("/generate-shapefile", tags=["Processing"])
async def generate_shapefile_for_edit(
    kml_zip: UploadFile = File(..., description="KML ZIP file"),
    spk_number: str = Form(..., description="SPK number"),
):
    if not FileUtils.validate_file_extension(kml_zip.filename, [".zip"]):
        raise InvalidFileFormatError("File must be a ZIP archive")

    work_dir = FileUtils.create_request_work_dir()
    cleanup = BackgroundTask(FileUtils.cleanup_dir, work_dir)

    try:
        zip_path = await FileUtils.save_upload_file(kml_zip, work_dir, "data.zip")
        FileUtils.extract_zip(zip_path, work_dir)

        merged_gdf = KMLParser.parse_kmls(work_dir)
        edit_zip = ShapefileService.create_shapefile_for_edit(merged_gdf, spk_number, work_dir)

        return FileResponse(
            path=edit_zip,
            filename=f"{spk_number}_zones_for_edit.zip",
            media_type="application/zip",
            background=cleanup,
            headers={"X-Total-Zones": str(len(merged_gdf))},
        )
    except Exception:
        FileUtils.cleanup_dir(work_dir)
        raise


@router.post("/process", tags=["Processing"])
async def process_complete_workflow(
    kml_zip: UploadFile = File(..., description="KML ZIP file"),
    excel_file: UploadFile = File(..., description="Excel file with flight records"),
    spk_number: str = Form(..., description="SPK number"),
    key_id: str = Form(..., description="Key ID"),
    edited_shapefile: UploadFile = File(None, description="Optional: edited shapefile ZIP from QGIS"),
):
    if not FileUtils.validate_file_extension(kml_zip.filename, [".zip"]):
        raise InvalidFileFormatError("KML file must be a ZIP archive")
    if not FileUtils.validate_file_extension(excel_file.filename, [".xlsx", ".xls", ".xlsm"]):
        raise InvalidFileFormatError("Excel file must be .xlsx, .xls, or .xlsm")

    work_dir = FileUtils.create_request_work_dir()
    cleanup = BackgroundTask(FileUtils.cleanup_dir, work_dir)

    try:
        zip_path = await FileUtils.save_upload_file(kml_zip, work_dir, "data.zip")
        FileUtils.extract_zip(zip_path, work_dir)
        excel_path = await FileUtils.save_upload_file(excel_file, work_dir, "data.xlsx")

        if edited_shapefile:
            edited_zip_path = await FileUtils.save_upload_file(edited_shapefile, work_dir, "edited.zip")
            merged_gdf = ShapefileService.load_shapefile_from_zip(edited_zip_path, work_dir)
        else:
            merged_gdf = KMLParser.parse_kmls(work_dir)

        filtered_gdf, df_summary = ShapefileService.process_excel(
            excel_path, merged_gdf, spk_number, key_id
        )
        final_zip = ShapefileService.create_final_shapefile(
            filtered_gdf, df_summary, spk_number, work_dir
        )

        return FileResponse(
            path=final_zip,
            filename=f"{spk_number}_final_upload.zip",
            media_type="application/zip",
            background=cleanup,
            headers={"X-Total-Zones": str(len(filtered_gdf))},
        )
    except Exception:
        FileUtils.cleanup_dir(work_dir)
        raise


@router.post("/upload-to-arcgis", tags=["ArcGIS"])
async def upload_to_arcgis(
    final_zip: UploadFile = File(..., description="Final upload ZIP"),
    spk_number: str = Form(..., description="SPK number"),
    key_id: str = Form(..., description="Key ID"),
    height: Optional[float] = Form(None, description="Flight height (default: 2.5)"),
    width: Optional[float] = Form(None, description="Spray width (default: 5)"),
    speed: Optional[float] = Form(None, description="Flight speed (default: 3.5)"),
    gis_credentials: dict = Depends(get_user_gis_credentials),
):
    # Validate inputs BEFORE any destructive ArcGIS calls
    _validate_positive("height", height)
    _validate_positive("width", width)
    _validate_positive("speed", speed)
    if not FileUtils.validate_file_extension(final_zip.filename, [".zip"]):
        raise InvalidFileFormatError("Upload must be a ZIP archive")

    work_dir = FileUtils.create_request_work_dir()
    try:
        zip_path = await FileUtils.save_upload_file(final_zip, work_dir, "final_upload.zip")

        arcgis_service = ArcGISService(gis_credentials)

        check_result = arcgis_service.check_spk_exists(spk_number)
        upload_result = arcgis_service.upload_shapefile(zip_path, spk_number)
        if check_result["exists"]:
            delete_result = arcgis_service.delete_spk(spk_number)
        else:
            delete_result = {"message": "No existing data to delete"}

        edit_kwargs = {}
        if height is not None:
            edit_kwargs["height"] = height
        if width is not None:
            edit_kwargs["width"] = width
        if speed is not None:
            edit_kwargs["speed"] = speed
        apply_result = arcgis_service.apply_edits(upload_result, spk_number, key_id, **edit_kwargs)

        return JSONResponse({
            "success": True,
            "message": f"Successfully uploaded to ArcGIS. {delete_result.get('message', '')}",
            "upload_result": upload_result,
            "apply_edits_result": apply_result,
            "features_added": apply_result.get("features_added", 0),
        })
    finally:
        FileUtils.cleanup_dir(work_dir)
