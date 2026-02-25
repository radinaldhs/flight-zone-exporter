# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Flight Zone Exporter is a FastAPI REST API for processing drone flight KML files and uploading geospatial data to ArcGIS Feature Server. It integrates with Firebase/Firestore for user data, Midtrans for payment processing (Indonesian payment gateway), and ArcGIS for geospatial operations.

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # for testing

# Run development server
uvicorn app.main:app --reload

# Run tests (requires 80% coverage)
pytest

# Run specific test file
pytest tests/unit/test_kml_parser.py

# Run with coverage report
pytest --cov=app --cov-report=html
```

## Architecture

### Request Flow
Routes (thin controllers) → Services (business logic) → Firebase/External APIs

### Key Directories
- `app/api/routes/` - FastAPI route handlers
- `app/services/` - Business logic (user_service, payment_service, arcgis_service, kml_parser)
- `app/core/` - Shared infrastructure (config, security, dependencies, firebase client)
- `app/models/` - Pydantic schemas for request/response validation

### Authentication System
- Users register with ArcGIS credentials (validated against ArcGIS server)
- JWT tokens (7-day expiry) issued on login
- Protected routes use `get_current_active_user` dependency from `app.core.dependencies`
- Whitelisted users get free access; others require Midtrans payment

### Subscription Model
- `subscription_status`: inactive | active | expired | grace_period
- 3-day grace period after subscription expires (configurable)
- `is_subscription_active()` method on UserInDB checks access

### KML Processing Pipeline
1. User uploads ZIP with KML files
2. `KMLParser.parse_kmls()` extracts placemarks to GeoDataFrame
3. `ShapefileService` generates shapefile for QGIS editing
4. Processed shapefile uploaded to ArcGIS Feature Server

## External Integrations

- **Firebase/Firestore**: User data, payments, subscriptions (singleton in `app.core.firebase`)
- **Midtrans**: Payment gateway with webhook at `/api/payments/webhook`
- **ArcGIS**: Sinarmas Forestry portal - uses shared credentials from settings for uploads

## Environment Variables

Required in `.env` (see `.env.example`):
- `SECRET_KEY` - JWT signing key
- `FIREBASE_SERVICE_ACCOUNT_PATH` or `FIREBASE_SERVICE_ACCOUNT_JSON`
- `GIS_USERNAME`, `GIS_PASSWORD` - Shared ArcGIS credentials for uploads
- `MIDTRANS_SERVER_KEY`, `MIDTRANS_CLIENT_KEY` - Payment gateway
- `MONTHLY_SUBSCRIPTION_PRICE` - Default 4,000,000 IDR

## Testing

- Unit tests in `tests/unit/`, integration tests in `tests/integration/`
- Test fixtures for Firebase mocks, sample KML data in `conftest.py`
- pytest markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`

## Deployment

- **Render.com**: Python 3.11.9 (see `render.yaml`)
- **Docker**: Python 3.9-slim with GDAL system libraries
