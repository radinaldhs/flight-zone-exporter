from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import shutil
import pandas as pd

from app.models.schemas import (
    ShapefileGenerateResponse,
    ProcessCompleteResponse,
    UploadToArcGISResponse,
    KMLMetadata
)
from app.services.kml_parser import KMLParser
from app.services.shapefile_service import ShapefileService
from app.services.arcgis_service import ArcGISService
from app.utils.file_utils import FileUtils
from app.core.exceptions import InvalidFileFormatError

router = APIRouter()


@router.post("/generate-shapefile", response_model=ShapefileGenerateResponse, tags=["Processing"])
async def generate_shapefile_for_edit(
    kml_zip: UploadFile = File(..., description="KML ZIP file"),
    spk_number: str = Form(..., description="SPK number"),
):
    if not FileUtils.validate_file_extension(kml_zip.filename, ['.zip']):
        raise InvalidFileFormatError("File must be a ZIP archive")

    work_dir = FileUtils.get_work_dir()

    try:
        # Save and extract KML ZIP
        zip_path = await FileUtils.save_upload_file(kml_zip, work_dir, "data.zip")
        FileUtils.extract_zip(zip_path, work_dir)

        # Parse KMLs
        parser = KMLParser()
        merged_gdf = parser.parse_kmls(work_dir)

        # Create shapefile for editing
        shapefile_service = ShapefileService()
        edit_zip = shapefile_service.create_shapefile_for_edit(merged_gdf, spk_number, work_dir)

        # Copy to a permanent location for download
        output_file = Path("zones_for_edit.zip")
        shutil.copy(edit_zip, output_file)

        metadata = parser.extract_kml_metadata(merged_gdf)

        return {
            "success": True,
            "message": "Shapefile generated successfully for QGIS editing",
            "total_zones": metadata["total_zones"],
            "zone_names": metadata["zone_names"],
            "filename": output_file.name
        }

    finally:
        FileUtils.cleanup_work_dir(work_dir)


@router.get("/download/shapefile-for-edit", tags=["Processing"])
async def download_shapefile_for_edit():
    file_path = Path("zones_for_edit.zip")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found. Generate shapefile first.")

    return FileResponse(
        path=file_path,
        filename="zones_for_edit.zip",
        media_type="application/zip"
    )


@router.post("/process", response_model=ProcessCompleteResponse, tags=["Processing"])
async def process_complete_workflow(
    kml_zip: UploadFile = File(..., description="KML ZIP file"),
    excel_file: UploadFile = File(..., description="Excel file with flight records"),
    spk_number: str = Form(..., description="SPK number"),
    key_id: str = Form(..., description="Key ID"),
    edited_shapefile: UploadFile = File(None, description="Optional: edited shapefile ZIP from QGIS")
):
    if not FileUtils.validate_file_extension(kml_zip.filename, ['.zip']):
        raise InvalidFileFormatError("KML file must be a ZIP archive")

    if not FileUtils.validate_file_extension(excel_file.filename, ['.xlsx', '.xls', '.xlsm']):
        raise InvalidFileFormatError("Excel file must be .xlsx, .xls, or .xlsm")

    work_dir = FileUtils.get_work_dir()

    try:
        # Save and extract KML ZIP
        zip_path = await FileUtils.save_upload_file(kml_zip, work_dir, "data.zip")
        FileUtils.extract_zip(zip_path, work_dir)

        # Save Excel file
        excel_path = await FileUtils.save_upload_file(excel_file, work_dir, "data.xlsx")

        # Parse KMLs or load edited shapefile
        if edited_shapefile:
            shapefile_service = ShapefileService()
            edited_zip_path = await FileUtils.save_upload_file(edited_shapefile, work_dir, "edited.zip")
            merged_gdf = shapefile_service.load_shapefile_from_zip(edited_zip_path, work_dir)
        else:
            parser = KMLParser()
            merged_gdf = parser.parse_kmls(work_dir)

        # Process Excel and create final shapefile
        shapefile_service = ShapefileService()
        filtered_gdf = shapefile_service.process_excel(excel_path, merged_gdf, spk_number, key_id)

        # Build summary for final shapefile
        df_summary = pd.DataFrame({'Name': filtered_gdf['Name']})
        df_summary['SPKNumber'] = spk_number
        df_summary['KeyID'] = key_id

        # Create final shapefile ZIP
        final_zip = shapefile_service.create_final_shapefile(filtered_gdf, df_summary, spk_number, work_dir)

        # Copy to permanent location
        output_file = Path("final_upload.zip")
        shutil.copy(final_zip, output_file)

        return {
            "success": True,
            "message": "Processing completed successfully",
            "total_zones": len(filtered_gdf),
            "columns": filtered_gdf.columns.tolist(),
            "filename": output_file.name
        }

    finally:
        FileUtils.cleanup_work_dir(work_dir)


@router.get("/download/final-upload", tags=["Processing"])
async def download_final_upload():
    file_path = Path("final_upload.zip")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found. Process workflow first.")

    return FileResponse(
        path=file_path,
        filename="final_upload.zip",
        media_type="application/zip"
    )


@router.post("/upload-to-arcgis", response_model=UploadToArcGISResponse, tags=["ArcGIS"])
async def upload_to_arcgis(
    spk_number: str = Form(..., description="SPK number"),
    key_id: str = Form(..., description="Key ID"),
    final_zip: UploadFile = File(None, description="Optional: final upload ZIP (if not using pre-generated)")
):
    work_dir = FileUtils.get_work_dir()

    try:
        # Determine which file to use
        if final_zip:
            zip_path = await FileUtils.save_upload_file(final_zip, work_dir, "final_upload.zip")
        else:
            zip_path = Path("final_upload.zip")
            if not zip_path.exists():
                raise HTTPException(
                    status_code=404,
                    detail="No final upload ZIP found. Either upload one or run the process workflow first."
                )

        # Check and delete existing SPK if needed
        arcgis_service = ArcGISService()
        check_result = arcgis_service.check_spk_exists(spk_number)

        if check_result["exists"]:
            delete_result = arcgis_service.delete_spk(spk_number)
        else:
            delete_result = {"message": "No existing data to delete"}

        # Upload shapefile
        upload_result = arcgis_service.upload_shapefile(zip_path, spk_number)

        # Apply edits
        apply_result = arcgis_service.apply_edits(upload_result, spk_number, key_id)

        return {
            "success": True,
            "message": f"Successfully uploaded to ArcGIS. {delete_result.get('message', '')}",
            "upload_result": upload_result,
            "apply_edits_result": apply_result,
            "features_added": apply_result.get("features_added", 0)
        }

    finally:
        FileUtils.cleanup_work_dir(work_dir)
