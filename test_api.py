#!/usr/bin/env python3
"""
Simple test script to verify the FastAPI application setup.
Run this after installing dependencies to ensure everything is configured correctly.
"""

import sys
import requests
from pathlib import Path


def test_health_endpoint():
    """Test the health check endpoint"""
    print("Testing health endpoint...")
    try:
        response = requests.get("http://localhost:8000/api/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed!")
            print(f"   App: {data.get('app_name')}")
            print(f"   Version: {data.get('version')}")
            print(f"   Status: {data.get('status')}")
            return True
        else:
            print(f"❌ Health check failed with status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Make sure the server is running:")
        print("   uvicorn app.main:app --reload")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_root_endpoint():
    """Test the root endpoint"""
    print("\nTesting root endpoint...")
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Root endpoint working!")
            print(f"   Docs URL: {data.get('docs')}")
            return True
        else:
            print(f"❌ Root endpoint failed with status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def check_env_file():
    """Check if .env file exists"""
    print("\nChecking environment configuration...")
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env file found")
        return True
    else:
        print("⚠️  .env file not found. Create one with:")
        print("   GIS_AUTH_USERNAME=your_username")
        print("   GIS_AUTH_PASSWORD=your_password")
        print("   GIS_USERNAME=your_gis_username")
        print("   GIS_PASSWORD=your_gis_password")
        return False


def check_app_structure():
    """Check if app directory structure exists"""
    print("\nChecking application structure...")
    required_paths = [
        Path("app/main.py"),
        Path("app/api/routes"),
        Path("app/core/config.py"),
        Path("app/services/arcgis_service.py"),
        Path("app/models/schemas.py"),
    ]

    all_exist = True
    for path in required_paths:
        if path.exists():
            print(f"✅ {path} exists")
        else:
            print(f"❌ {path} not found")
            all_exist = False

    return all_exist


def main():
    print("=" * 60)
    print("Flight Zone Exporter API - Setup Verification")
    print("=" * 60)

    # Check structure
    structure_ok = check_app_structure()

    # Check env file
    env_ok = check_env_file()

    print("\n" + "=" * 60)
    print("API Endpoint Tests (requires running server)")
    print("=" * 60)

    # Test endpoints
    health_ok = test_health_endpoint()
    root_ok = test_root_endpoint()

    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    if structure_ok and env_ok and health_ok and root_ok:
        print("✅ All tests passed! Your API is ready to use.")
        print("\nNext steps:")
        print("1. Visit http://localhost:8000/docs for interactive API documentation")
        print("2. Check API_README.md for usage examples")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        if not (health_ok and root_ok):
            print("\nMake sure the API server is running:")
            print("   uvicorn app.main:app --reload")
        return 1


if __name__ == "__main__":
    sys.exit(main())
