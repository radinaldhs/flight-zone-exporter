import uuid
from datetime import datetime
from typing import Optional
from app.models.user import UserCreate, UserInDB, User
from app.core.security import get_password_hash, verify_password
from app.core.firebase import get_firestore_client


class UserService:
    @staticmethod
    def _get_users_collection():
        """Get Firestore users collection reference."""
        db = get_firestore_client()
        return db.collection('users')

    @staticmethod
    def get_user_by_gis_auth_username(gis_auth_username: str) -> Optional[UserInDB]:
        """Get user by GIS auth username."""
        try:
            users_ref = UserService._get_users_collection()
            query = users_ref.where('gis_auth_username', '==', gis_auth_username).limit(1)
            docs = query.stream()

            for doc in docs:
                user_data = doc.to_dict()
                user_data['id'] = doc.id

                # Convert Firestore Timestamp to datetime if needed
                if 'created_at' in user_data and hasattr(user_data['created_at'], 'seconds'):
                    user_data['created_at'] = datetime.fromtimestamp(user_data['created_at'].seconds)

                return UserInDB(**user_data)

            return None
        except Exception as e:
            print(f"Error getting user by username: {e}")
            return None

    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[UserInDB]:
        """Get user by ID."""
        try:
            users_ref = UserService._get_users_collection()
            doc = users_ref.document(user_id).get()

            if doc.exists:
                user_data = doc.to_dict()
                user_data['id'] = doc.id

                # Convert Firestore Timestamp to datetime if needed
                if 'created_at' in user_data and hasattr(user_data['created_at'], 'seconds'):
                    user_data['created_at'] = datetime.fromtimestamp(user_data['created_at'].seconds)

                return UserInDB(**user_data)

            return None
        except Exception as e:
            print(f"Error getting user by ID: {e}")
            return None

    @staticmethod
    def create_user(user_create: UserCreate) -> UserInDB:
        """Create a new user."""
        # Check if user already exists
        if UserService.get_user_by_gis_auth_username(user_create.gis_auth_username):
            raise ValueError("User with this GIS Auth Username already exists")

        # Create new user
        user_id = str(uuid.uuid4())
        user_data = {
            "gis_auth_username": user_create.gis_auth_username,
            "full_name": user_create.full_name,
            "hashed_gis_auth_password": get_password_hash(user_create.gis_auth_password),
            "gis_auth_password": user_create.gis_auth_password,  # Store plain for ArcGIS
            "is_active": True,
            "created_at": datetime.utcnow()
        }

        try:
            # Store in Firestore
            users_ref = UserService._get_users_collection()
            users_ref.document(user_id).set(user_data)

            # Return UserInDB object
            user_data['id'] = user_id
            user_data['created_at'] = user_data['created_at'].isoformat()
            return UserInDB(**user_data)
        except Exception as e:
            print(f"Error creating user: {e}")
            raise ValueError(f"Failed to create user: {str(e)}")

    @staticmethod
    def authenticate_user(gis_auth_username: str, gis_auth_password: str) -> Optional[UserInDB]:
        """Authenticate user with GIS auth credentials."""
        user = UserService.get_user_by_gis_auth_username(gis_auth_username)

        if not user:
            return None

        if not verify_password(gis_auth_password, user.hashed_gis_auth_password):
            return None

        return user

    @staticmethod
    def get_user_gis_credentials(user_id: str) -> Optional[dict]:
        """Get user's GIS credentials for ArcGIS operations."""
        from app.core.config import settings
        user = UserService.get_user_by_id(user_id)

        if not user:
            return None

        return {
            "GIS_AUTH_USERNAME": user.gis_auth_username,
            "GIS_AUTH_PASSWORD": user.gis_auth_password,  # Plain password for ArcGIS
            "GIS_USERNAME": settings.GIS_USERNAME,  # From .env - shared credential
            "GIS_PASSWORD": settings.GIS_PASSWORD   # From .env - shared credential
        }
