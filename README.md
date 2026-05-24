# Flight Zone Exporter

A modern REST API built with FastAPI for processing drone flight KML files and uploading to ArcGIS Feature Server.

### Features

- **REST API**: Full RESTful API with automatic OpenAPI documentation
- **Service-Oriented Architecture**: Business logic separated into service modules
- **Type Safety**: Pydantic models for request/response validation
- **Production Ready**: Proper error handling, logging, and CORS support
- **Stateless**: No session state, easier to scale and deploy
- **Docker Ready**: Easy containerization and deployment

## Quick Start

### Installation

```bash
git clone https://github.com/yourusername/flight-zone-exporter.git
cd flight-zone-exporter
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration

Copy `.env.example` to `.env` and fill in the required secrets:

```env
SECRET_KEY=...        # python -c "import secrets; print(secrets.token_urlsafe(32))"
ENCRYPTION_KEY=...    # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
GIS_USERNAME=...      # shared ArcGIS editor account used for uploads
GIS_PASSWORD=...
FIREBASE_SERVICE_ACCOUNT_PATH=firebase-service-account.json
CORS_ORIGINS=http://localhost:5173
```

Each user provides their own Sinarmas portal credentials at registration (used for
their per-request step-1 token); the shared editor account in `GIS_USERNAME`/`GIS_PASSWORD`
is used for the actual upload write.

### Running the API

```bash
uvicorn app.main:app --reload
```

Visit:
- API: http://localhost:8000
- Interactive Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/api/health

## 📖 Documentation

See **[API_README.md](API_README.md)** for complete API documentation including:
- All available endpoints
- Request/response examples
- Usage workflows
- Python client examples
- Deployment guides

## Features

- **KML Processing**: Parse KML files and extract flight zone data
- **Shapefile Generation**: Convert KML to shapefiles for QGIS editing
- **Excel Integration**: Process flight records from Excel files
- **ArcGIS Integration**: Upload processed data to ArcGIS Feature Server
- **SPK Management**: Check and delete existing SPK data
- **Automatic Documentation**: Interactive API docs via Swagger UI

## Architecture

```
app/
├── main.py                    # FastAPI entry point
├── api/routes/               # API endpoints
├── core/                     # Config & exceptions
├── models/                   # Pydantic schemas
├── services/                 # Business logic
└── utils/                    # Utilities
```

## License

© 2025 Radinal Dewantara Husein
