import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    APP_NAME: str = "Flight Zone Exporter API"
    VERSION: str = "2.0.0"
    DEBUG: bool = False

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production-min-32-chars")

    # Firebase Configuration
    FIREBASE_SERVICE_ACCOUNT_PATH: str = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "")
    FIREBASE_SERVICE_ACCOUNT_JSON: str = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "")

    # ArcGIS Configuration
    ARCGIS_BASE_URL: str = os.getenv(
        "ARCGIS_BASE_URL",
        "https://maps.sinarmasforestry.com/arcgis/rest/services/PreFo/DroneSprayingVendor/FeatureServer/0"
    )
    ARCGIS_SERVER_URL: str = os.getenv(
        "ARCGIS_SERVER_URL",
        "https://maps.sinarmasforestry.com/arcgis/rest/services/PreFo/DroneSprayingVendor/MapServer"
    )
    ARCGIS_TOKEN_URL: str = os.getenv(
        "ARCGIS_TOKEN_URL",
        "https://maps.sinarmasforestry.com/portal/sharing/rest/generateToken"
    )
    ARCGIS_UPLOAD_URL: str = os.getenv(
        "ARCGIS_UPLOAD_URL",
        "https://maps.sinarmasforestry.com/portal/sharing/rest/content/features/generate"
    )
    ARCGIS_REFERER: str = os.getenv(
        "ARCGIS_REFERER",
        "https://maps.sinarmasforestry.com/UploadDroneManagements/"
    )

    # ArcGIS Credentials
    GIS_AUTH_USERNAME: str = os.getenv("GIS_AUTH_USERNAME", "")
    GIS_AUTH_PASSWORD: str = os.getenv("GIS_AUTH_PASSWORD", "")
    GIS_USERNAME: str = os.getenv("GIS_USERNAME", "")
    GIS_PASSWORD: str = os.getenv("GIS_PASSWORD", "")

    # File Processing
    WORK_DIR: str = "working"
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB

    # CORS
    CORS_ORIGINS: list = ["*"]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
