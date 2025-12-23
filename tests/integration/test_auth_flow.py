import pytest
from fastapi import status
from app.core.security import get_password_hash
from app.models.user import UserInDB
from datetime import datetime

class TestAuthFlow:
    def test_register_new_user(self, client, mock_firebase_user, mock_sinarmas_validation):
        """Test user registration with GIS_AUTH credentials validated on Sinarmas portal"""
        # Sinarmas portal validates credentials
        mock_sinarmas_validation.return_value = True

        response = client.post("/api/auth/register", json={
            "gis_auth_username": "agasha123",
            "gis_auth_password": "ValidPass123!",
            "full_name": "Test User"
        })

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "access_token" in data
        assert data["user"]["gis_auth_username"] == "test_gis_user"

    def test_register_invalid_sinarmas_credentials(self, client, mock_firebase_user, mock_sinarmas_validation):
        """Test registration with invalid Sinarmas portal credentials"""
        # Sinarmas portal rejects credentials
        mock_sinarmas_validation.return_value = False

        response = client.post("/api/auth/register", json={
            "gis_auth_username": "invalid_user",
            "gis_auth_password": "WrongPass123!",
            "full_name": "Test User"
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid GIS Auth credentials" in response.json()["detail"]

    def test_login_success(self, client, mock_firebase_user):
        """Test successful login with GIS_AUTH credentials"""
        # Mock authenticate to return a valid user
        mock_firebase_user['authenticate'].return_value = UserInDB(
            id='user123',
            gis_auth_username='agasha123',
            full_name='Test User',
            hashed_gis_auth_password=get_password_hash("password123"),
            is_active=True,
            created_at=datetime.utcnow()
        )

        response = client.post("/api/auth/login", json={
            "gis_auth_username": "agasha123",
            "gis_auth_password": "password123"
        })

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["user"]["gis_auth_username"] == "agasha123"

    def test_login_invalid_credentials(self, client, mock_firebase_user):
        """Test login with invalid credentials"""
        # authenticate returns None for invalid credentials
        mock_firebase_user['authenticate'].return_value = None

        response = client.post("/api/auth/login", json={
            "gis_auth_username": "nonexistent",
            "gis_auth_password": "wrongpass"
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_wrong_password(self, client, mock_firebase_user):
        """Test login with correct username but wrong password"""
        # authenticate returns None for wrong password
        mock_firebase_user['authenticate'].return_value = None

        response = client.post("/api/auth/login", json={
            "gis_auth_username": "agasha123",
            "gis_auth_password": "wrongpassword"
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user(self, client, mock_firebase_user, mocker):
        """Test getting current authenticated user"""
        # Mock authenticate for login
        test_user = UserInDB(
            id='user123',
            gis_auth_username='agasha123',
            full_name='Test User',
            hashed_gis_auth_password=get_password_hash("password123"),
            is_active=True,
            created_at=datetime.utcnow()
        )
        mock_firebase_user['authenticate'].return_value = test_user

        # Login to get token
        login_response = client.post("/api/auth/login", json={
            "gis_auth_username": "agasha123",
            "gis_auth_password": "password123"
        })

        token = login_response.json()["access_token"]

        # Mock get_user_by_id for the /me endpoint
        mock_get_by_id = mocker.patch('app.services.user_service.UserService.get_user_by_id')
        mock_get_by_id.return_value = test_user

        # Get current user with token
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["gis_auth_username"] == "agasha123"

    def test_get_current_user_without_token(self, client):
        """Test accessing protected endpoint without token"""
        response = client.get("/api/auth/me")

        # FastAPI returns 403 for missing credentials
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
