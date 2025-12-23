import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
import tempfile
import shutil
from pathlib import Path

@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)

@pytest.fixture
def temp_work_dir():
    """Create temporary working directory"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def sample_kml_file():
    """Load sample KML file"""
    return Path(__file__).parent / "fixtures" / "sample.kml"

@pytest.fixture
def sample_kml_zip():
    """Load sample KML ZIP"""
    return Path(__file__).parent / "fixtures" / "sample_zones.zip"

@pytest.fixture
def sample_excel_file():
    """Load sample Excel file"""
    return Path(__file__).parent / "fixtures" / "sample_excel.xlsx"

@pytest.fixture
def sample_shapefile_zip():
    """Load sample shapefile ZIP"""
    return Path(__file__).parent / "fixtures" / "sample_shapefile.zip"

@pytest.fixture
def mock_arcgis_auth(mocker):
    """Mock ArcGIS authentication"""
    mock_service = mocker.patch('app.services.arcgis_service.ArcGISService.authenticate')
    mock_service.return_value = "fake_token_12345"
    return mock_service

@pytest.fixture
def mock_firebase_user(mocker):
    """Mock Firebase user operations"""
    from app.models.user import UserInDB
    from datetime import datetime

    # Mock get user by gis_auth_username
    mock_get = mocker.patch('app.services.user_service.UserService.get_user_by_gis_auth_username')
    mock_get.return_value = None  # User doesn't exist by default

    # Mock create user
    mock_create = mocker.patch('app.services.user_service.UserService.create_user')
    mock_create.return_value = UserInDB(
        id='user123',
        gis_auth_username='test_gis_user',
        full_name='Test User',
        hashed_gis_auth_password='$2b$12$hashed_password',
        is_active=True,
        created_at=datetime.utcnow()
    )

    # Mock authenticate user
    mock_auth = mocker.patch('app.services.user_service.UserService.authenticate_user')
    mock_auth.return_value = None  # Not authenticated by default

    return {'get': mock_get, 'create': mock_create, 'authenticate': mock_auth}

@pytest.fixture
def mock_sinarmas_validation(mocker):
    """Mock Sinarmas portal GIS_AUTH validation"""
    mock_validate = mocker.patch('app.services.arcgis_service.ArcGISService.validate_gis_auth_credentials')
    mock_validate.return_value = True  # Valid by default
    return mock_validate
