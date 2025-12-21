import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
from app.models.user import UserCreate, UserInDB, User
from app.core.security import get_password_hash, verify_password

# Simple file-based storage (can be replaced with database later)
USERS_FILE = Path("users.json")


class UserService:
    @staticmethod
    def _load_users() -> Dict[str, dict]:
        if not USERS_FILE.exists():
            return {}

        with open(USERS_FILE, 'r') as f:
            return json.load(f)

    @staticmethod
    def _save_users(users: Dict[str, dict]):
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f, indent=2, default=str)

    @staticmethod
    def get_user_by_username(username: str) -> Optional[UserInDB]:
        users = UserService._load_users()

        for user_id, user_data in users.items():
            if user_data.get('username') == username:
                return UserInDB(**user_data)

        return None

    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[UserInDB]:
        users = UserService._load_users()
        user_data = users.get(user_id)

        if user_data:
            return UserInDB(**user_data)

        return None

    @staticmethod
    def create_user(user_create: UserCreate) -> UserInDB:
        users = UserService._load_users()

        # Check if user already exists
        if UserService.get_user_by_username(user_create.username):
            raise ValueError("User with this username already exists")

        # Create new user
        user_id = str(uuid.uuid4())
        user_data = {
            "id": user_id,
            "username": user_create.username,
            "full_name": user_create.full_name,
            "hashed_password": get_password_hash(user_create.password),
            "gis_auth_username": user_create.gis_auth_username,
            "gis_auth_password": user_create.gis_auth_password,
            "gis_username": user_create.gis_username,
            "gis_password": user_create.gis_password,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat()
        }

        users[user_id] = user_data
        UserService._save_users(users)

        return UserInDB(**user_data)

    @staticmethod
    def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
        user = UserService.get_user_by_username(username)

        if not user:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        return user

    @staticmethod
    def get_user_gis_credentials(user_id: str) -> Optional[dict]:
        user = UserService.get_user_by_id(user_id)

        if not user:
            return None

        return {
            "GIS_AUTH_USERNAME": user.gis_auth_username,
            "GIS_AUTH_PASSWORD": user.gis_auth_password,
            "GIS_USERNAME": user.gis_username,
            "GIS_PASSWORD": user.gis_password
        }
