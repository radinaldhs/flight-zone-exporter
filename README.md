# Flight Zone Exporter

A modern REST API built with FastAPI for processing drone flight KML files and uploading to ArcGIS Feature Server.

## 🚀 Version 2.0 - FastAPI Migration

This project has been refactored from Streamlit to **FastAPI** for better scalability, API-first design, and production readiness.

### What's New in v2.0

- **REST API**: Full RESTful API with automatic OpenAPI documentation
- **Better Architecture**: Separated business logic into service modules
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

Create a `.env` file:
```env
GIS_AUTH_USERNAME=your_username
GIS_AUTH_PASSWORD=your_password
GIS_USERNAME=your_gis_username
GIS_PASSWORD=your_gis_password
```

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

## Migration from Streamlit

The original Streamlit app is preserved in [runner.py](runner.py). The new FastAPI version offers:

- **API-first design** for easy integration
- **Better separation of concerns** with service modules
- **Type safety** with Pydantic
- **Production-ready** error handling and logging
- **Scalable** stateless architecture

To use the old Streamlit app:
```bash
pip install streamlit
streamlit run runner.py
```

## License

© 2025 Radinal Dewantara Husein
