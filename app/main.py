from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.core.config import settings
from app.core.exceptions import (
    ArcGISAuthenticationError,
    ArcGISUploadError,
    FileProcessingError,
    SPKNotFoundError,
    InvalidFileFormatError
)
from app.api.routes import health, arcgis, kml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="REST API for processing drone flight KML files and uploading to ArcGIS Feature Server",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api")
app.include_router(arcgis.router, prefix="/api/arcgis")
app.include_router(kml.router, prefix="/api/kml")


# Global exception handlers
@app.exception_handler(ArcGISAuthenticationError)
async def arcgis_auth_exception_handler(request, exc):
    logger.error(f"ArcGIS Authentication Error: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(ArcGISUploadError)
async def arcgis_upload_exception_handler(request, exc):
    logger.error(f"ArcGIS Upload Error: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(FileProcessingError)
async def file_processing_exception_handler(request, exc):
    logger.error(f"File Processing Error: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(SPKNotFoundError)
async def spk_not_found_exception_handler(request, exc):
    logger.warning(f"SPK Not Found: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(InvalidFileFormatError)
async def invalid_file_format_exception_handler(request, exc):
    logger.warning(f"Invalid File Format: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.on_event("startup")
async def startup_event():
    logger.info(f"{settings.APP_NAME} v{settings.VERSION} starting up...")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"{settings.APP_NAME} shutting down...")


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/api/health"
    }


# Serverless handler for Vercel/AWS Lambda
from mangum import Mangum
handler = Mangum(app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
