import pytest
from app.core.security import get_password_hash, verify_password, create_access_token, decode_access_token

class TestSecurity:
    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)

        assert hashed != password
        assert verify_password(password, hashed) == True
        assert verify_password("WrongPassword", hashed) == False

    def test_password_hash_different_each_time(self):
        """Test that same password generates different hashes"""
        password = "TestPassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # Hashes should be different due to salt
        assert hash1 != hash2
        # But both should verify correctly
        assert verify_password(password, hash1) == True
        assert verify_password(password, hash2) == True

    def test_create_access_token(self):
        """Test JWT token creation"""
        token = create_access_token(data={"sub": "user123", "gis_auth_username": "gis_user"})

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50

    def test_decode_access_token(self):
        """Test JWT token decoding"""
        data = {"sub": "user123", "gis_auth_username": "gis_user"}
        token = create_access_token(data=data)

        decoded = decode_access_token(token)
        assert decoded["sub"] == "user123"
        assert decoded["gis_auth_username"] == "gis_user"
        assert "exp" in decoded  # Expiration should be added

    def test_decode_invalid_token(self):
        """Test decoding invalid token returns None"""
        result = decode_access_token("invalid.token.here")
        assert result is None

    def test_decode_expired_token(self):
        """Test decoding expired token returns None"""
        # Create a token that expires immediately
        from datetime import timedelta
        token = create_access_token(
            data={"sub": "user123"},
            expires_delta=timedelta(seconds=-1)  # Already expired
        )

        result = decode_access_token(token)
        assert result is None

    def test_empty_password(self):
        """Test empty password handling"""
        # Empty passwords are hashed normally by bcrypt
        empty_hash = get_password_hash("")
        assert verify_password("", empty_hash) == True
        assert verify_password("notempty", empty_hash) == False
