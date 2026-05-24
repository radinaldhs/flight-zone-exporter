# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Flight Zone Exporter is a FastAPI REST API for processing drone flight KML files and uploading geospatial data to ArcGIS Feature Server. It uses Firebase/Firestore for user storage and the Sinarmas Forestry ArcGIS portal for token-based uploads.

A Vue frontend lives in a sibling repo at `../flight-zone-exporter-vue` and talks to this API via `VITE_API_URL` (defaults to `http://localhost:8000`).

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
Routes (thin controllers) → Services (business logic) → Firebase / ArcGIS

### Key Directories
- `app/api/routes/` — FastAPI route handlers (`auth`, `health`, `arcgis`, `kml`)
- `app/services/` — Business logic (`user_service`, `arcgis_service`, `kml_parser`, `shapefile_service`)
- `app/core/` — Shared infrastructure (`config`, `security`, `encryption`, `dependencies`, `firebase`, `exceptions`)
- `app/models/` — Pydantic schemas for request/response validation
- `app/utils/` — File helpers (request-scoped work dirs, zip extraction with zip-slip guard)

### Authentication & GIS credentials
- Users register with their Sinarmas ArcGIS portal credentials (validated against `maps.sinarmasforestry.com` at registration).
- The portal password is bcrypt-hashed (for login) and Fernet-encrypted (so it can be replayed to ArcGIS for the step-1 token).
- The step-3 upload token uses a single **shared editor account** (`GIS_USERNAME`/`GIS_PASSWORD` from env) — every authenticated user uploads through that account; their per-user identity flows through step-1 so the audit trail is preserved.
- JWTs (7-day expiry) are issued on register/login; protected routes use `get_current_active_user`.
- `get_user_gis_credentials` (in `app.core.dependencies`) returns a bundle: per-user auth creds (decrypted from Firestore) + shared editor creds (from settings). Raises 503 if the shared creds aren't configured.

### ArcGIS token cache
`ArcGISService` keeps a process-wide token cache keyed by `(auth_username, editor_username)` with a TTL of `ARCGIS_TOKEN_TTL_SECONDS` (default 3000s). One token lookup costs 3 sequential ArcGIS round-trips, so caching is load-bearing.

### KML processing pipeline
1. Client uploads a ZIP of KML files (+ Excel for the full workflow).
2. Each request gets its own work dir under `WORK_DIR/<uuid>/` — no cross-request file collisions.
3. `KMLParser.parse_kmls()` extracts placemarks into a GeoDataFrame.
4. `ShapefileService` generates a shapefile zip for QGIS editing, or merges Excel data into a final upload zip.
5. `/api/kml/process` and `/api/kml/generate-shapefile` return the resulting zip *inline* via `FileResponse`; cleanup runs as a `BackgroundTask` after the response is sent.
6. `/api/kml/upload-to-arcgis` accepts the final zip in the same request and pushes it through `check_spk_exists → delete_spk → upload_shapefile → apply_edits`. Numeric inputs (`height`/`width`/`speed`) are validated *before* any destructive call.

## External Integrations

- **Firebase/Firestore**: user records (singleton client in `app.core.firebase`)
- **ArcGIS**: Sinarmas Forestry portal — token URLs, feature server, dashboard layer (all configurable via env)

## Environment Variables

Required (app fails to start otherwise):
- `SECRET_KEY` — JWT signing key
- `ENCRYPTION_KEY` — Fernet key for at-rest GIS-credential encryption
- `FIREBASE_SERVICE_ACCOUNT_PATH` *or* `FIREBASE_SERVICE_ACCOUNT_JSON`

Required for ArcGIS/KML routes (server boots without them, but those routes return 503):
- `GIS_USERNAME`, `GIS_PASSWORD` — shared ArcGIS editor account used for upload tokens

Optional (have safe defaults):
- `CORS_ORIGINS` (comma-separated; default `http://localhost:3000`)
- `CORS_ALLOW_CREDENTIALS` (default `true`; auto-disabled if origins is `*`)
- `ARCGIS_*` endpoint URLs and `ARCGIS_TOKEN_TTL_SECONDS`
- `WORK_DIR` (default `working`)

See `.env.example` for the full template.

## Testing

- Unit tests in `tests/unit/`, integration tests in `tests/integration/`
- Test fixtures in `tests/conftest.py` (Firebase mocks, sample KML/shapefile/Excel under `tests/fixtures/`)
- Pytest markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`
- Coverage gate: 80% (`pytest.ini`)

## Deployment

- **Render.com**: Python 3.11.9 (`render.yaml`). Production target.
- **Docker**: Python 3.11-slim with GDAL system libraries (`Dockerfile`).

Vercel/Lambda is **not** supported — geopandas + GDAL exceeds the 50 MB function
size cap and KML processing exceeds the execution-time cap.
