import os
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from typing_extensions import Annotated
from dotenv import load_dotenv

load_dotenv()


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Required environment variable {name} is not set. "
            "Refer to .env.example for configuration."
        )
    return value


class Settings(BaseSettings):
    APP_NAME: str = "Flight Zone Exporter API"
    VERSION: str = "2.0.0"
    DEBUG: bool = False

    # Security — both must be set; no production-unsafe defaults
    SECRET_KEY: str = _require_env("SECRET_KEY")
    # Fernet key (urlsafe base64-encoded 32 bytes). Generate with:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ENCRYPTION_KEY: str = _require_env("ENCRYPTION_KEY")

    # Shared ArcGIS editor credentials (used as the step-3 token holder for uploads).
    # These are server-side infrastructure secrets shared by all users.
    # Stored as empty defaults so the server can boot for /health and /docs without them;
    # get_user_gis_credentials raises a clear error if a request needs them and they're absent.
    GIS_USERNAME: str = os.getenv("GIS_USERNAME", "")
    GIS_PASSWORD: str = os.getenv("GIS_PASSWORD", "")

    # Firebase Configuration
    FIREBASE_SERVICE_ACCOUNT_PATH: str = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "")
    FIREBASE_SERVICE_ACCOUNT_JSON: str = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "")

    # ArcGIS endpoint configuration (not secrets — safe to ship defaults)
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
    ARCGIS_DASHBOARD_URL: str = os.getenv(
        "ARCGIS_DASHBOARD_URL",
        "https://maps.sinarmasforestry.com/arcgis/rest/services/PreFo/DroneSprayingDashboard/MapServer/1"
    )

    # ArcGIS token cache TTL (seconds). Tokens are requested with expiration=60 (minutes);
    # cache slightly less to be safe.
    ARCGIS_TOKEN_TTL_SECONDS: int = int(os.getenv("ARCGIS_TOKEN_TTL_SECONDS", "3000"))

    # File processing
    WORK_DIR: str = os.getenv("WORK_DIR", "working")
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100 MB

    # CORS — comma-separated origins, or "*" for any (credentials disabled in that case)
    CORS_ORIGINS: Annotated[List[str], NoDecode] = ["http://localhost:3000"]
    CORS_ALLOW_CREDENTIALS: bool = True

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_cors_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")


settings = Settings()
