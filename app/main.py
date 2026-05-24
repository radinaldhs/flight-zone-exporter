import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import arcgis, auth, health, kml
from app.core.config import settings
from app.core.exceptions import (
    ArcGISAuthenticationError,
    ArcGISUploadError,
    FileProcessingError,
    InvalidFileFormatError,
    SPKNotFoundError,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("%s v%s starting up...", settings.APP_NAME, settings.VERSION)
    yield
    logger.info("%s shutting down...", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="REST API for processing drone flight KML files and uploading to ArcGIS Feature Server",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — "*" + credentials is invalid per spec; disable credentials in that case.
_wildcard = settings.CORS_ORIGINS == ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False if _wildcard else settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Zones", "Content-Disposition"],
)

app.include_router(auth.router, prefix="/api/auth")
app.include_router(health.router, prefix="/api")
app.include_router(arcgis.router, prefix="/api/arcgis")
app.include_router(kml.router, prefix="/api/kml")


def _exc_response(exc):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(ArcGISAuthenticationError)
async def _arcgis_auth_handler(request, exc):
    logger.error("ArcGIS Authentication Error: %s", exc.detail)
    return _exc_response(exc)


@app.exception_handler(ArcGISUploadError)
async def _arcgis_upload_handler(request, exc):
    logger.error("ArcGIS Upload Error: %s", exc.detail)
    return _exc_response(exc)


@app.exception_handler(FileProcessingError)
async def _file_processing_handler(request, exc):
    logger.error("File Processing Error: %s", exc.detail)
    return _exc_response(exc)


@app.exception_handler(SPKNotFoundError)
async def _spk_not_found_handler(request, exc):
    logger.warning("SPK Not Found: %s", exc.detail)
    return _exc_response(exc)


@app.exception_handler(InvalidFileFormatError)
async def _invalid_file_format_handler(request, exc):
    logger.warning("Invalid File Format: %s", exc.detail)
    return _exc_response(exc)


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/api/health",
    }


# Serverless handler for Vercel/AWS Lambda
from mangum import Mangum  # noqa: E402

handler = Mangum(app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
