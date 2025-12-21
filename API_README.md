# Flight Zone Exporter API

A modern REST API built with FastAPI for processing drone flight KML files and uploading to ArcGIS Feature Server.

## Features

- **KML Processing**: Parse KML files and extract flight zone data
- **Shapefile Generation**: Convert KML to shapefiles for QGIS editing
- **Excel Integration**: Process flight records from Excel files
- **ArcGIS Integration**: Upload processed data to ArcGIS Feature Server
- **SPK Management**: Check and delete existing SPK data
- **Automatic API Documentation**: Interactive docs via Swagger UI

## Quick Start

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/flight-zone-exporter.git
cd flight-zone-exporter
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
Create a `.env` file in the root directory:
```env
GIS_AUTH_USERNAME=your_username
GIS_AUTH_PASSWORD=your_password
GIS_USERNAME=your_gis_username
GIS_PASSWORD=your_gis_password
```

### Running the API

#### Development Mode (with auto-reload)
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Production Mode
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at:
- Main API: http://localhost:8000
- Interactive Docs (Swagger): http://localhost:8000/docs
- Alternative Docs (ReDoc): http://localhost:8000/redoc

## API Endpoints

### Health Check

#### `GET /api/health`
Check API health status.

**Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "app_name": "Flight Zone Exporter API"
}
```

### ArcGIS Operations

#### `POST /api/arcgis/spk/check`
Check if SPK exists in ArcGIS.

**Request Body:**
```json
{
  "spk_number": "SPK-001"
}
```

**Response:**
```json
{
  "exists": true,
  "count": 5,
  "spk": "SPK-001",
  "oids": [1, 2, 3, 4, 5]
}
```

#### `DELETE /api/arcgis/spk`
Delete existing SPK data from ArcGIS.

**Request Body:**
```json
{
  "spk_number": "SPK-001"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Deleted 5 objects for SPK SPK-001",
  "deleted_count": 5,
  "oids": [1, 2, 3, 4, 5]
}
```

### KML Processing

#### `POST /api/kml/generate-shapefile`
Generate shapefile from KML for QGIS editing.

**Request (multipart/form-data):**
- `kml_zip` (file): ZIP file containing KML files
- `spk_number` (string): SPK number

**Example using cURL:**
```bash
curl -X POST "http://localhost:8000/api/kml/generate-shapefile" \
  -F "kml_zip=@/path/to/kml.zip" \
  -F "spk_number=SPK-001"
```

**Response:**
```json
{
  "success": true,
  "message": "Shapefile generated successfully for QGIS editing",
  "total_zones": 10,
  "zone_names": ["Zone1", "Zone2", ...],
  "filename": "zones_for_edit.zip"
}
```

#### `GET /api/kml/download/shapefile-for-edit`
Download the generated shapefile for editing.

**Example:**
```bash
curl -O "http://localhost:8000/api/kml/download/shapefile-for-edit"
```

#### `POST /api/kml/process`
Complete processing workflow (KML + Excel → Final Shapefile).

**Request (multipart/form-data):**
- `kml_zip` (file): ZIP file containing KML files
- `excel_file` (file): Excel file with flight records
- `spk_number` (string): SPK number
- `key_id` (string): Key ID
- `edited_shapefile` (file, optional): Edited shapefile ZIP from QGIS

**Example using cURL:**
```bash
curl -X POST "http://localhost:8000/api/kml/process" \
  -F "kml_zip=@/path/to/kml.zip" \
  -F "excel_file=@/path/to/data.xlsx" \
  -F "spk_number=SPK-001" \
  -F "key_id=KEY-001"
```

**With edited shapefile:**
```bash
curl -X POST "http://localhost:8000/api/kml/process" \
  -F "kml_zip=@/path/to/kml.zip" \
  -F "excel_file=@/path/to/data.xlsx" \
  -F "spk_number=SPK-001" \
  -F "key_id=KEY-001" \
  -F "edited_shapefile=@/path/to/edited.zip"
```

**Response:**
```json
{
  "success": true,
  "message": "Processing completed successfully",
  "total_zones": 8,
  "columns": ["Name", "Height", "Route_Spacing", ...],
  "filename": "final_upload.zip"
}
```

#### `GET /api/kml/download/final-upload`
Download the final processed shapefile.

**Example:**
```bash
curl -O "http://localhost:8000/api/kml/download/final-upload"
```

#### `POST /api/kml/upload-to-arcgis`
Upload processed shapefile to ArcGIS Feature Server.

**Request (multipart/form-data):**
- `spk_number` (string): SPK number
- `key_id` (string): Key ID
- `final_zip` (file, optional): Final upload ZIP (if not using pre-generated)

**Example using cURL:**
```bash
curl -X POST "http://localhost:8000/api/kml/upload-to-arcgis" \
  -F "spk_number=SPK-001" \
  -F "key_id=KEY-001"
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully uploaded to ArcGIS. Deleted 5 objects for SPK SPK-001",
  "upload_result": { ... },
  "apply_edits_result": { ... },
  "features_added": 8
}
```

## Workflows

### Workflow 1: Quick Upload (No QGIS Editing)

1. Process KML and Excel files:
```bash
curl -X POST "http://localhost:8000/api/kml/process" \
  -F "kml_zip=@kml.zip" \
  -F "excel_file=@data.xlsx" \
  -F "spk_number=SPK-001" \
  -F "key_id=KEY-001"
```

2. Upload to ArcGIS:
```bash
curl -X POST "http://localhost:8000/api/kml/upload-to-arcgis" \
  -F "spk_number=SPK-001" \
  -F "key_id=KEY-001"
```

### Workflow 2: With QGIS Editing

1. Generate shapefile for editing:
```bash
curl -X POST "http://localhost:8000/api/kml/generate-shapefile" \
  -F "kml_zip=@kml.zip" \
  -F "spk_number=SPK-001"
```

2. Download shapefile:
```bash
curl -O "http://localhost:8000/api/kml/download/shapefile-for-edit"
```

3. Edit in QGIS (manual step)

4. Process with edited shapefile:
```bash
curl -X POST "http://localhost:8000/api/kml/process" \
  -F "kml_zip=@kml.zip" \
  -F "excel_file=@data.xlsx" \
  -F "spk_number=SPK-001" \
  -F "key_id=KEY-001" \
  -F "edited_shapefile=@edited.zip"
```

5. Upload to ArcGIS:
```bash
curl -X POST "http://localhost:8000/api/kml/upload-to-arcgis" \
  -F "spk_number=SPK-001" \
  -F "key_id=KEY-001"
```

## Python Client Example

```python
import requests

BASE_URL = "http://localhost:8000"

# Check SPK
response = requests.post(
    f"{BASE_URL}/api/arcgis/spk/check",
    json={"spk_number": "SPK-001"}
)
print(response.json())

# Process files
files = {
    "kml_zip": open("kml.zip", "rb"),
    "excel_file": open("data.xlsx", "rb")
}
data = {
    "spk_number": "SPK-001",
    "key_id": "KEY-001"
}
response = requests.post(
    f"{BASE_URL}/api/kml/process",
    files=files,
    data=data
)
print(response.json())

# Upload to ArcGIS
response = requests.post(
    f"{BASE_URL}/api/kml/upload-to-arcgis",
    data={
        "spk_number": "SPK-001",
        "key_id": "KEY-001"
    }
)
print(response.json())
```

## Error Handling

The API uses standard HTTP status codes:

- `200 OK`: Successful request
- `400 Bad Request`: Invalid file format or parameters
- `401 Unauthorized`: ArcGIS authentication failed
- `404 Not Found`: Resource not found (e.g., SPK not found)
- `422 Unprocessable Entity`: File processing error
- `500 Internal Server Error`: Server error

Error responses follow this format:
```json
{
  "detail": "Error message describing what went wrong"
}
```

## Architecture

```
app/
├── main.py                    # FastAPI application entry point
├── api/
│   └── routes/               # API endpoint handlers
│       ├── health.py         # Health check
│       ├── arcgis.py         # ArcGIS operations
│       └── kml.py            # KML processing
├── core/
│   ├── config.py             # Configuration and settings
│   └── exceptions.py         # Custom exceptions
├── models/
│   └── schemas.py            # Pydantic models
├── services/
│   ├── arcgis_service.py     # ArcGIS API interactions
│   ├── kml_parser.py         # KML parsing logic
│   └── shapefile_service.py  # Shapefile generation
└── utils/
    └── file_utils.py         # File handling utilities
```

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black app/
```

### Type Checking
```bash
mypy app/
```

## Deployment

### Docker Deployment

Create a `Dockerfile`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY .env .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t flight-zone-exporter .
docker run -p 8000:8000 --env-file .env flight-zone-exporter
```

## Migration from Streamlit

The old Streamlit app ([runner.py](runner.py)) has been refactored into this FastAPI application with the following improvements:

1. **Separation of Concerns**: Business logic extracted into service modules
2. **Type Safety**: Pydantic models for request/response validation
3. **Error Handling**: Comprehensive exception handling with proper HTTP status codes
4. **API-First**: RESTful API design for easy integration
5. **Automatic Documentation**: Interactive API docs via Swagger UI
6. **Stateless Design**: No session state, easier to scale
7. **Production Ready**: CORS support, logging, proper error handling

The old Streamlit app is kept in [runner.py](runner.py) for reference.

## License

© 2025 Radinal Dewantara Husein

## Support

For issues and questions, please open an issue on GitHub.
