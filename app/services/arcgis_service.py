import json
import logging
import time
import datetime
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from app.core.config import settings
from app.core.exceptions import (
    ArcGISAuthenticationError,
    ArcGISUploadError,
    SPKNotFoundError,
)

logger = logging.getLogger(__name__)


def _quote_arcgis(value: str) -> str:
    """
    Escape a value for safe inclusion inside a single-quoted ArcGIS where clause.
    Doubles single quotes per SQL string-literal escaping rules.
    """
    if value is None:
        return ""
    return str(value).replace("'", "''")


class ArcGISService:
    # Process-wide token cache: { (gis_auth_username, gis_username): (token, expires_at_epoch) }
    _token_cache: Dict[Tuple[str, str], Tuple[str, float]] = {}
    _token_cache_lock = threading.Lock()

    def __init__(self, gis_credentials: Optional[dict] = None):
        if not gis_credentials:
            raise ArcGISAuthenticationError("GIS credentials are required")

        required = ("GIS_AUTH_USERNAME", "GIS_AUTH_PASSWORD", "GIS_USERNAME", "GIS_PASSWORD")
        missing = [k for k in required if not gis_credentials.get(k)]
        if missing:
            raise ArcGISAuthenticationError(f"Missing GIS credentials: {', '.join(missing)}")

        self._creds = gis_credentials
        self.base_url = settings.ARCGIS_BASE_URL
        self.server_url = settings.ARCGIS_SERVER_URL
        self.token_url = settings.ARCGIS_TOKEN_URL
        self.upload_url = settings.ARCGIS_UPLOAD_URL
        self.token_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": settings.ARCGIS_REFERER,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        }

    @staticmethod
    def validate_gis_credentials(username: str, password: str) -> bool:
        """Validate a single credential pair against the ArcGIS portal."""
        try:
            response = requests.post(
                settings.ARCGIS_TOKEN_URL,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Referer": settings.ARCGIS_REFERER,
                },
                data={
                    "request": "getToken",
                    "username": username,
                    "password": password,
                    "expiration": "60",
                    "referer": "https://maps.sinarmasforestry.com",
                    "f": "json",
                },
                timeout=30,
            )
            return bool(response.json().get("token"))
        except Exception:
            logger.exception("Error validating GIS credentials")
            return False

    def _get_token_uncached(self) -> str:
        session = requests.Session()
        auth_user = self._creds["GIS_AUTH_USERNAME"]
        auth_pass = self._creds["GIS_AUTH_PASSWORD"]
        editor_user = self._creds["GIS_USERNAME"]
        editor_pass = self._creds["GIS_PASSWORD"]

        step1 = session.post(
            self.token_url,
            headers=self.token_headers,
            data={
                "request": "getToken",
                "username": auth_user,
                "password": auth_pass,
                "expiration": "60",
                "referer": "https://maps.sinarmasforestry.com",
                "f": "json",
            },
            timeout=30,
        ).json()
        if not step1.get("token"):
            raise ArcGISAuthenticationError("Failed step 1: initial login")

        step2 = session.post(
            self.token_url,
            headers=self.token_headers,
            data={
                "request": "getToken",
                "serverUrl": self.server_url,
                "token": step1["token"],
                "referer": "https://maps.sinarmasforestry.com",
                "f": "json",
            },
            timeout=30,
        ).json()
        if not step2.get("token"):
            raise ArcGISAuthenticationError("Failed step 2: scoped token")

        step3 = session.post(
            self.token_url,
            headers=self.token_headers,
            data={
                "request": "getToken",
                "username": editor_user,
                "password": editor_pass,
                "expiration": "60",
                "referer": "https://maps.sinarmasforestry.com",
                "f": "json",
            },
            timeout=30,
        ).json()
        if not step3.get("token"):
            raise ArcGISAuthenticationError("Failed step 3: final login")

        return step3["token"]

    def get_token(self) -> str:
        key = (self._creds["GIS_AUTH_USERNAME"], self._creds["GIS_USERNAME"])
        now = time.time()

        with self._token_cache_lock:
            cached = self._token_cache.get(key)
            if cached and cached[1] > now:
                return cached[0]

        token = self._get_token_uncached()
        expires_at = now + settings.ARCGIS_TOKEN_TTL_SECONDS
        with self._token_cache_lock:
            self._token_cache[key] = (token, expires_at)
        return token

    def _invalidate_token(self) -> None:
        key = (self._creds["GIS_AUTH_USERNAME"], self._creds["GIS_USERNAME"])
        with self._token_cache_lock:
            self._token_cache.pop(key, None)

    def query_spk(self, spk: str) -> List[int]:
        token = self.get_token()
        response = requests.get(
            f"{self.base_url}/query",
            params={
                "f": "json",
                "where": f"SPKNumber='{_quote_arcgis(spk)}'",
                "outFields": "OBJECTID",
                "returnGeometry": "false",
                "token": token,
            },
            timeout=30,
        )
        data = response.json()
        return [f["attributes"]["OBJECTID"] for f in data.get("features", [])]

    def delete_spk(self, spk: str) -> Dict[str, Any]:
        token = self.get_token()
        oids = self.query_spk(spk)
        if not oids:
            raise SPKNotFoundError(spk)

        deleted_count = 0
        for oid in oids:
            response = requests.post(
                f"{self.base_url}/applyEdits",
                headers=self.token_headers,
                data={"f": "json", "deletes": str(oid), "token": token},
                timeout=30,
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
            "oids": oids,
        }

    def upload_shapefile(self, zip_path: Path, spk_number: str) -> Dict[str, Any]:
        token = self.get_token()

        with open(zip_path, "rb") as f:
            response = requests.post(
                self.upload_url,
                params={
                    "filetype": "shapefile",
                    "publishParameters": json.dumps({
                        "name": f"UploadedZone_{spk_number}",
                        "targetSR": {"wkid": 4326},
                        "maxRecordCount": 1000,
                        "enforceInputFileSizeLimit": True,
                        "enforceOutputJsonSizeLimit": True,
                    }),
                    "f": "json",
                    "token": token,
                },
                files={
                    "file": ("final_upload.zip", f, "application/zip"),
                    "token": (None, token),
                },
                timeout=120,
            )

        if not response.ok:
            raise ArcGISUploadError(f"Upload failed: {response.status_code} {response.text}")
        return response.json()

    def apply_edits(
        self,
        upload_response: Dict[str, Any],
        spk_number: str,
        key_id: str,
        height: float = 2.5,
        width: float = 5,
        speed: float = 3.5,
    ) -> Dict[str, Any]:
        token = self.get_token()
        features = (
            upload_response.get("featureCollection", {})
            .get("layers", [])[0]
            .get("featureSet", {})
            .get("features", [])
        )

        now_ms = int(time.time() * 1000)
        adds = []
        for feat in features:
            attrs = feat.get("attributes", {})
            start_ts = end_ts = now_ms

            for field, target in (("StarFlight", "start"), ("EndFlight", "end")):
                raw = attrs.get(field, "")
                if raw:
                    try:
                        parsed = int(
                            datetime.datetime.strptime(raw, "%Y-%m-%d %H:%M:%S").timestamp() * 1000
                        )
                        if target == "start":
                            start_ts = parsed
                        else:
                            end_ts = parsed
                    except ValueError:
                        pass

            adds.append({
                "aggregateGeometries": None,
                "geometry": feat["geometry"],
                "symbol": None,
                "attributes": {
                    "FlightID": attrs.get("Name"),
                    "DroneID": attrs.get("Flight_Con"),
                    "DroneCapacity": attrs.get("DroneCapacity", 25),
                    "SPKNumber": spk_number,
                    "KeyID": key_id,
                    "StartFlight": start_ts,
                    "EndFlight": end_ts,
                    "ProcessedDate": now_ms,
                    "Height": height,
                    "Width": width,
                    "Speed": speed,
                    "TaskArea": attrs.get("Task_Area", 0),
                    "SprayAmount": attrs.get("Spray_amou", 0),
                    "VendorName": "PT SENTRA AGASHA NUSANTARA",
                    "UserID": self._creds["GIS_AUTH_USERNAME"],
                    "CRT_Date": now_ms,
                },
            })

        response = requests.post(
            f"{self.base_url}/applyEdits?token={token}",
            data={"f": "json", "adds": json.dumps(adds)},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=120,
        )

        if not response.ok:
            raise ArcGISUploadError(f"Apply edits failed: {response.status_code}")

        return {
            "success": True,
            "response": response.json(),
            "features_added": len(adds),
        }

    def query_dashboard(self, where: str, out_fields: str) -> List[Dict[str, Any]]:
        token = self.get_token()
        response = requests.get(
            f"{settings.ARCGIS_DASHBOARD_URL}/query",
            params={
                "f": "json",
                "where": where,
                "outFields": out_fields,
                "returnDistinctValues": "true",
                "returnGeometry": "false",
                "spatialRel": "esriSpatialRelIntersects",
                "token": token,
            },
            headers=self.token_headers,
            timeout=30,
        )
        data = response.json()
        if "error" in data:
            raise ArcGISUploadError(
                f"Dashboard query failed: {data['error'].get('message', str(data['error']))}"
            )
        return [f["attributes"] for f in data.get("features", [])]

    def get_regions(self, vendor_code: str) -> List[str]:
        where = f"VendorCode='{_quote_arcgis(vendor_code)}' AND Region<>'' AND Drone=0"
        results = self.query_dashboard(where, "Region")
        return sorted({r["Region"] for r in results})

    def get_districts(self, vendor_code: str, region: str) -> List[str]:
        where = (
            f"VendorCode='{_quote_arcgis(vendor_code)}' "
            f"AND Region='{_quote_arcgis(region)}' "
            f"AND District<>'' AND Drone=0"
        )
        results = self.query_dashboard(where, "District")
        return sorted({r["District"] for r in results})

    def get_petaks(self, vendor_code: str, district: str) -> List[str]:
        where = (
            f"VendorCode='{_quote_arcgis(vendor_code)}' "
            f"AND District='{_quote_arcgis(district)}' "
            f"AND Drone=0"
        )
        results = self.query_dashboard(where, "Petak")
        return sorted({r["Petak"] for r in results})

    def get_spk_numbers(self, vendor_code: str, petak: str) -> List[Dict[str, str]]:
        where = (
            f"VendorCode='{_quote_arcgis(vendor_code)}' "
            f"AND Petak='{_quote_arcgis(petak)}' "
            f"AND Drone=0"
        )
        results = self.query_dashboard(where, "SPKNumber,Activity")
        seen: set = set()
        unique: List[Dict[str, str]] = []
        for r in results:
            key = (r["SPKNumber"], r["Activity"])
            if key not in seen:
                seen.add(key)
                unique.append({"spk_number": r["SPKNumber"], "activity": r["Activity"]})
        return sorted(unique, key=lambda x: x["spk_number"])

    def check_spk_exists(self, spk: str) -> Dict[str, Any]:
        oids = self.query_spk(spk)
        return {
            "exists": len(oids) > 0,
            "count": len(oids),
            "spk": spk,
            "oids": oids,
        }
