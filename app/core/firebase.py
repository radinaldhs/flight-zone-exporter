import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from typing import Optional

_db: Optional[firestore.Client] = None


def initialize_firebase():
    """Initialize Firebase Admin SDK with service account credentials."""
    global _db

    if _db is not None:
        return _db

    try:
        # Check if Firebase service account key is provided
        service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")

        if service_account_path and os.path.exists(service_account_path):
            # Initialize with service account file
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
        else:
            # Try to initialize with environment variable JSON
            service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")

            if service_account_json:
                # Parse JSON from environment variable
                service_account_dict = json.loads(service_account_json)
                cred = credentials.Certificate(service_account_dict)
                firebase_admin.initialize_app(cred)
            else:
                raise ValueError(
                    "Firebase credentials not found. Please set either "
                    "FIREBASE_SERVICE_ACCOUNT_PATH or FIREBASE_SERVICE_ACCOUNT_JSON"
                )

        _db = firestore.client()
        print("Firebase initialized successfully")
        return _db

    except Exception as e:
        print(f"Error initializing Firebase: {e}")
        raise


def get_firestore_client() -> firestore.Client:
    """Get Firestore client instance."""
    global _db

    if _db is None:
        _db = initialize_firebase()

    return _db
