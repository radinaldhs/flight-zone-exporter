import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings
from app.core.encryption import decrypt, encrypt
from app.core.firebase import get_firestore_client
from app.core.security import get_password_hash, verify_password
from app.models.user import UserCreate, UserInDB

logger = logging.getLogger(__name__)


class UserService:
    @staticmethod
    def _get_users_collection():
        db = get_firestore_client()
        return db.collection("users")

    @staticmethod
    def _doc_to_user(doc) -> UserInDB:
        user_data = doc.to_dict()
        user_data["id"] = doc.id
        created_at = user_data.get("created_at")
        if created_at is not None and hasattr(created_at, "seconds"):
            user_data["created_at"] = datetime.fromtimestamp(created_at.seconds, tz=timezone.utc)
        return UserInDB(**user_data)

    @staticmethod
    def get_user_by_gis_auth_username(gis_auth_username: str) -> Optional[UserInDB]:
        try:
            users_ref = UserService._get_users_collection()
            docs = users_ref.where("gis_auth_username", "==", gis_auth_username).limit(1).stream()
            for doc in docs:
                return UserService._doc_to_user(doc)
            return None
        except Exception:
            logger.exception("Error getting user by username")
            return None

    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[UserInDB]:
        try:
            doc = UserService._get_users_collection().document(user_id).get()
            if doc.exists:
                return UserService._doc_to_user(doc)
            return None
        except Exception:
            logger.exception("Error getting user by ID")
            return None

    @staticmethod
    def create_user(user_create: UserCreate) -> UserInDB:
        if UserService.get_user_by_gis_auth_username(user_create.gis_auth_username):
            raise ValueError("User with this GIS Auth Username already exists")

        user_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)
        user_data = {
            "gis_auth_username": user_create.gis_auth_username,
            "full_name": user_create.full_name,
            "hashed_gis_auth_password": get_password_hash(user_create.gis_auth_password),
            "encrypted_gis_auth_password": encrypt(user_create.gis_auth_password),
            "is_active": True,
            "created_at": created_at,
        }

        try:
            UserService._get_users_collection().document(user_id).set(user_data)
        except Exception as e:
            logger.exception("Error creating user")
            raise ValueError(f"Failed to create user: {e}") from e

        return UserInDB(id=user_id, **user_data)

    @staticmethod
    def authenticate_user(gis_auth_username: str, gis_auth_password: str) -> Optional[UserInDB]:
        user = UserService.get_user_by_gis_auth_username(gis_auth_username)
        if not user:
            return None
        if not verify_password(gis_auth_password, user.hashed_gis_auth_password):
            return None
        return user

    @staticmethod
    def get_user_gis_credentials(user_id: str) -> Optional[dict]:
        """
        Return the credential bundle for ArcGIS calls:
          - per-user auth creds, decrypted from Firestore (step-1 token)
          - shared editor creds from settings (step-3 token)
        Returns None if the user is missing or stored ciphertext can't be decrypted.
        """
        user = UserService.get_user_by_id(user_id)
        if not user:
            return None

        try:
            auth_password = decrypt(user.encrypted_gis_auth_password)
        except ValueError:
            logger.exception("Failed to decrypt auth password for user %s", user_id)
            return None

        return {
            "GIS_AUTH_USERNAME": user.gis_auth_username,
            "GIS_AUTH_PASSWORD": auth_password,
            "GIS_USERNAME": settings.GIS_USERNAME,
            "GIS_PASSWORD": settings.GIS_PASSWORD,
        }
