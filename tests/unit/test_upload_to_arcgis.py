import math
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestUploadToArcGISParams:
    """Unit tests for the height/width/speed parameters on the upload-to-arcgis route."""

    def _post(self, client, data: dict, zip_path: Path = None):
        """Helper that posts to /api/kml/upload-to-arcgis with the given form data."""
        return client.post("/api/kml/upload-to-arcgis", data=data)

    def _arcgis_patches(self, mocker):
        """Patch all ArcGIS service methods so no network calls are made."""
        check = mocker.patch(
            "app.api.routes.kml.ArcGISService.check_spk_exists",
            return_value={"exists": False}
        )
        upload = mocker.patch(
            "app.api.routes.kml.ArcGISService.upload_shapefile",
            return_value={"featureCollection": {"layers": [{"featureSet": {"features": []}}]}}
        )
        apply = mocker.patch(
            "app.api.routes.kml.ArcGISService.apply_edits",
            return_value={"success": True, "features_added": 0}
        )
        return check, upload, apply

    def _ensure_final_zip(self, tmp_path: Path):
        """Write a dummy final_upload.zip so the route can find it."""
        final_zip = Path("final_upload.zip")
        final_zip.write_bytes(b"PK")  # minimal placeholder
        return final_zip

    @pytest.fixture(autouse=True)
    def cleanup_final_zip(self):
        yield
        final_zip = Path("final_upload.zip")
        if final_zip.exists():
            final_zip.unlink()

    # ------------------------------------------------------------------
    # Validation: invalid values must return 422
    # ------------------------------------------------------------------

    def test_negative_height_returns_422(self, client, mocker):
        self._arcgis_patches(mocker)
        self._ensure_final_zip(Path("."))

        response = self._post(client, {"spk_number": "SPK001", "key_id": "KEY001", "height": -1.0})

        assert response.status_code == 422

    def test_zero_height_returns_422(self, client, mocker):
        self._arcgis_patches(mocker)
        self._ensure_final_zip(Path("."))

        response = self._post(client, {"spk_number": "SPK001", "key_id": "KEY001", "height": 0})

        assert response.status_code == 422

    def test_negative_width_returns_422(self, client, mocker):
        self._arcgis_patches(mocker)
        self._ensure_final_zip(Path("."))

        response = self._post(client, {"spk_number": "SPK001", "key_id": "KEY001", "width": -5.0})

        assert response.status_code == 422

    def test_zero_speed_returns_422(self, client, mocker):
        self._arcgis_patches(mocker)
        self._ensure_final_zip(Path("."))

        response = self._post(client, {"spk_number": "SPK001", "key_id": "KEY001", "speed": 0})

        assert response.status_code == 422

    def test_negative_speed_returns_422(self, client, mocker):
        self._arcgis_patches(mocker)
        self._ensure_final_zip(Path("."))

        response = self._post(client, {"spk_number": "SPK001", "key_id": "KEY001", "speed": -3.5})

        assert response.status_code == 422

    # ------------------------------------------------------------------
    # Custom valid values are forwarded to apply_edits
    # ------------------------------------------------------------------

    def test_custom_height_forwarded_to_apply_edits(self, client, mocker):
        _, _, apply = self._arcgis_patches(mocker)
        self._ensure_final_zip(Path("."))

        self._post(client, {"spk_number": "SPK001", "key_id": "KEY001", "height": 4.0})

        _, kwargs = apply.call_args
        assert kwargs.get("height") == 4.0

    def test_custom_width_forwarded_to_apply_edits(self, client, mocker):
        _, _, apply = self._arcgis_patches(mocker)
        self._ensure_final_zip(Path("."))

        self._post(client, {"spk_number": "SPK001", "key_id": "KEY001", "width": 8.0})

        _, kwargs = apply.call_args
        assert kwargs.get("width") == 8.0

    def test_custom_speed_forwarded_to_apply_edits(self, client, mocker):
        _, _, apply = self._arcgis_patches(mocker)
        self._ensure_final_zip(Path("."))

        self._post(client, {"spk_number": "SPK001", "key_id": "KEY001", "speed": 5.5})

        _, kwargs = apply.call_args
        assert kwargs.get("speed") == 5.5

    # ------------------------------------------------------------------
    # Omitted params: apply_edits called WITHOUT the key so its own
    # defaults (height=2.5, width=5, speed=3.5) take effect.
    # ------------------------------------------------------------------

    def test_omitted_height_not_in_apply_edits_kwargs(self, client, mocker):
        _, _, apply = self._arcgis_patches(mocker)
        self._ensure_final_zip(Path("."))

        self._post(client, {"spk_number": "SPK001", "key_id": "KEY001"})

        _, kwargs = apply.call_args
        assert "height" not in kwargs

    def test_omitted_width_not_in_apply_edits_kwargs(self, client, mocker):
        _, _, apply = self._arcgis_patches(mocker)
        self._ensure_final_zip(Path("."))

        self._post(client, {"spk_number": "SPK001", "key_id": "KEY001"})

        _, kwargs = apply.call_args
        assert "width" not in kwargs

    def test_omitted_speed_not_in_apply_edits_kwargs(self, client, mocker):
        _, _, apply = self._arcgis_patches(mocker)
        self._ensure_final_zip(Path("."))

        self._post(client, {"spk_number": "SPK001", "key_id": "KEY001"})

        _, kwargs = apply.call_args
        assert "speed" not in kwargs

    # ------------------------------------------------------------------
    # apply_edits signature: defaults used when kwargs are not supplied
    # ------------------------------------------------------------------

    def test_apply_edits_default_height(self):
        from app.services.arcgis_service import ArcGISService

        service = ArcGISService.__new__(ArcGISService)
        import inspect
        sig = inspect.signature(service.apply_edits)
        assert sig.parameters["height"].default == 2.5

    def test_apply_edits_default_width(self):
        from app.services.arcgis_service import ArcGISService

        service = ArcGISService.__new__(ArcGISService)
        import inspect
        sig = inspect.signature(service.apply_edits)
        assert sig.parameters["width"].default == 5

    def test_apply_edits_default_speed(self):
        from app.services.arcgis_service import ArcGISService

        service = ArcGISService.__new__(ArcGISService)
        import inspect
        sig = inspect.signature(service.apply_edits)
        assert sig.parameters["speed"].default == 3.5
