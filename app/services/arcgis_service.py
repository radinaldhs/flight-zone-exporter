import json
import time
import datetime
import requests
from pathlib import Path
from typing import Dict, List, Any

from app.core.config import settings
from app.core.exceptions import (
    ArcGISAuthenticationError,
    ArcGISUploadError,
    SPKNotFoundError
)


class ArcGISService:
    def __init__(self):
        self.base_url = settings.ARCGIS_BASE_URL
        self.server_url = settings.ARCGIS_SERVER_URL
        self.token_url = settings.ARCGIS_TOKEN_URL
        self.upload_url = settings.ARCGIS_UPLOAD_URL
        self.token_headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': settings.ARCGIS_REFERER,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            'sec-ch-ua-platform': '"macOS"',
            'sec-ch-ua-mobile': '?0',
        }

    def get_token(self) -> str:
        session = requests.Session()

        # Step 1: Initial authentication
        step1 = session.post(self.token_url, headers=self.token_headers, data={
            'request': 'getToken',
            'username': settings.GIS_AUTH_USERNAME,
            'password': settings.GIS_AUTH_PASSWORD,
            'expiration': '60',
            'referer': 'https://maps.sinarmasforestry.com',
            'f': 'json'
        }).json()

        step1_token = step1.get('token')
        if not step1_token:
            raise ArcGISAuthenticationError("Failed step 1: initial login")

        # Step 2: Scoped token for MapServer
        step2 = session.post(self.token_url, headers=self.token_headers, data={
            'request': 'getToken',
            'serverUrl': self.server_url,
            'token': step1_token,
            'referer': 'https://maps.sinarmasforestry.com',
            'f': 'json'
        }).json()

        scoped_token = step2.get('token')
        if not scoped_token:
            raise ArcGISAuthenticationError("Failed step 2: scoped token")

        # Step 3: Final authentication
        step3 = session.post(self.token_url, headers=self.token_headers, data={
            'request': 'getToken',
            'username': settings.GIS_USERNAME,
            'password': settings.GIS_PASSWORD,
            'expiration': '60',
            'referer': 'https://maps.sinarmasforestry.com',
            'f': 'json'
        }).json()

        final_token = step3.get('token')
        if not final_token:
            raise ArcGISAuthenticationError("Failed step 3: final login")

        return final_token

    def query_spk(self, spk: str) -> List[int]:
        session = requests.Session()
        token = self.get_token()

        response = session.get(f"{self.base_url}/query", params={
            'f': 'json',
            'where': f"SPKNumber='{spk}'",
            'outFields': 'OBJECTID',
            'returnGeometry': 'false',
            'token': token
        })

        data = response.json()
        oids = [f['attributes']['OBJECTID'] for f in data.get('features', [])]
        return oids

    def delete_spk(self, spk: str) -> Dict[str, Any]:
        session = requests.Session()
        token = self.get_token()

        oids = self.query_spk(spk)
        if not oids:
            raise SPKNotFoundError(spk)

        deleted_count = 0
        for oid in oids:
            response = session.post(
                f"{self.base_url}/applyEdits",
                headers=self.token_headers,
                data={
                    'f': 'json',
                    'deletes': str(oid),
                    'token': token
                }
            )
            if not response.ok:
                raise ArcGISUploadError(
                    f"Delete failed for OBJECTID {oid}: {response.status_code}"
                )
            deleted_count += 1

        return {
            "success": True,
            "message": f"Deleted {deleted_count} objects for SPK {spk}",
            "deleted_count": deleted_count,
            "oids": oids
        }

    def upload_shapefile(self, zip_path: Path, spk_number: str) -> Dict[str, Any]:
        session = requests.Session()
        token = self.get_token()

        with open(zip_path, 'rb') as f:
            files = {
                'file': ('final_upload.zip', f, 'application/zip'),
                'token': (None, token)
            }
            response = session.post(
                self.upload_url,
                params={
                    'filetype': 'shapefile',
                    'publishParameters': json.dumps({
                        'name': f'UploadedZone_{spk_number}',
                        'maxRecordCount': 1000,
                        'enforceInputFileSizeLimit': True,
                        'enforceOutputJsonSizeLimit': True,
                    }),
                    'f': 'json',
                    'token': token
                },
                files=files
            )

        if not response.ok:
            raise ArcGISUploadError(f"Upload failed: {response.status_code} {response.text}")

        return response.json()

    def apply_edits(self, upload_response: Dict[str, Any], spk_number: str, key_id: str) -> Dict[str, Any]:
        token = self.get_token()
        apply_url = f"{self.base_url}/applyEdits?token={token}"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        features = upload_response.get("featureCollection", {}).get("layers", [])[0].get('featureSet', {}).get("features", [])

        adds = []
        for feat in features:
            start_flight = feat["attributes"].get("StartFlight", "")
            end_flight = feat["attributes"].get("EndFlight", "")

            start_timestamp = 0
            end_timestamp = 0

            if start_flight:
                try:
                    start_timestamp = int(datetime.datetime.strptime(start_flight, "%Y-%m-%d %H:%M:%S").timestamp() * 1000)
                except ValueError:
                    pass

            if end_flight:
                try:
                    end_timestamp = int(datetime.datetime.strptime(end_flight, "%Y-%m-%d %H:%M:%S").timestamp() * 1000)
                except ValueError:
                    pass

            adds.append({
                "aggregateGeometries": None,
                "geometry": feat["geometry"],
                "symbol": None,
                "attributes": {
                    "FlightID": feat["attributes"].get("Name"),
                    "DroneID": feat["attributes"].get("Flight_Con"),
                    "DroneCapacity": feat["attributes"].get("DroneCapacity", 25),
                    "SPKNumber": spk_number,
                    "KeyID": key_id,
                    "StartFlight": start_timestamp,
                    "EndFlight": end_timestamp,
                    "ProcessedDate": int(time.time() * 1000),
                    "Height": feat["attributes"].get("Height", 0),
                    "Width": feat["attributes"].get("Route_Spac", 0),
                    "Speed": feat["attributes"].get("Task_Fligh", 0),
                    "TaskArea": feat["attributes"].get("Task_Area", 0),
                    "SprayAmount": feat["attributes"].get("Spray_amou", 0),
                    "VendorName": "PT SENTRA AGASHA NUSANTARA",
                    "UserID": settings.GIS_AUTH_USERNAME,
                    "CRT_Date": int(time.time() * 1000),
                }
            })

        payload = {
            "f": "json",
            "adds": json.dumps(adds)
        }

        response = requests.post(apply_url, data=payload, headers=headers)

        if not response.ok:
            raise ArcGISUploadError(f"Apply edits failed: {response.status_code}")

        return {
            "success": True,
            "response": response.json(),
            "features_added": len(adds)
        }

    def check_spk_exists(self, spk: str) -> Dict[str, Any]:
        oids = self.query_spk(spk)
        return {
            "exists": len(oids) > 0,
            "count": len(oids),
            "spk": spk,
            "oids": oids
        }
