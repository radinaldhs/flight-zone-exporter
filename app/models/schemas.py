from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict


class ProcessRequest(BaseModel):
    spk_number: str = Field(..., description="SPK number")
    key_id: str = Field(..., description="Key ID")


class SPKDeleteRequest(BaseModel):
    spk_number: str = Field(..., description="SPK number to delete")


class SPKCheckResponse(BaseModel):
    exists: bool
    count: int
    spk: str
    oids: List[int]


class SPKDeleteResponse(BaseModel):
    success: bool
    message: str
    deleted_count: int
    oids: List[int]


class ShapefileGenerateResponse(BaseModel):
    success: bool
    message: str
    total_zones: int
    zone_names: List[str]
    filename: str


class ProcessCompleteResponse(BaseModel):
    success: bool
    message: str
    total_zones: int
    columns: List[str]
    filename: str


class UploadToArcGISResponse(BaseModel):
    success: bool
    message: str
    upload_result: Dict[str, Any]
    apply_edits_result: Dict[str, Any]
    features_added: int


class KMLMetadata(BaseModel):
    total_zones: int
    columns: List[str]
    zone_names: List[str]
    bounds: Optional[List[float]]
    crs: str


class HealthResponse(BaseModel):
    status: str
    version: str
    app_name: str


class ErrorResponse(BaseModel):
    detail: str
