"""Unit tests for ArcGISService — HTTP-200 error detection and feature-count fixes."""
import io
import json
import pytest

from app.core.exceptions import ArcGISUploadError
from app.services.arcgis_service import ArcGISService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_CREDS = {
    "GIS_AUTH_USERNAME": "auth_user",
    "GIS_AUTH_PASSWORD": "auth_pass",
    "GIS_USERNAME": "editor_user",
    "GIS_PASSWORD": "editor_pass",
}

ONE_FEATURE_UPLOAD = {
    "featureCollection": {
        "layers": [{
            "featureSet": {
                "features": [{
                    "geometry": {"paths": [[[0, 0], [1, 1]]]},
                    "attributes": {
                        "Name": "R1",
                        "Flight_Con": "D1",
                    },
                }]
            }
        }]
    }
}

TWO_FEATURE_UPLOAD = {
    "featureCollection": {
        "layers": [{
            "featureSet": {
                "features": [
                    {
                        "geometry": {"paths": [[[0, 0], [1, 1]]]},
                        "attributes": {"Name": "R1", "Flight_Con": "D1"},
                    },
                    {
                        "geometry": {"paths": [[[2, 2], [3, 3]]]},
                        "attributes": {"Name": "R2", "Flight_Con": "D2"},
                    },
                ]
            }
        }]
    }
}


class FakeResponse:
    def __init__(self, body: dict, *, ok: bool = True, status_code: int = 200):
        self._body = body
        self.ok = ok
        self.status_code = status_code
        self.text = json.dumps(body)

    def json(self):
        return self._body


def _make_service(mocker) -> ArcGISService:
    """Construct ArcGISService with get_token pre-patched to return a dummy token."""
    mocker.patch.object(ArcGISService, "get_token", return_value="tok")
    return ArcGISService(gis_credentials=VALID_CREDS)


# ---------------------------------------------------------------------------
# upload_shapefile tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_upload_shapefile_raises_on_error_body(mocker, tmp_path):
    """HTTP 200 body containing `error` dict must raise ArcGISUploadError with detail text."""
    svc = _make_service(mocker)
    error_body = {
        "error": {
            "code": 400,
            "message": "Invalid shapefile",
            "details": ["Internal error during object insert."],
        }
    }
    mocker.patch("requests.post", return_value=FakeResponse(error_body))
    zip_path = tmp_path / "upload.zip"
    zip_path.write_bytes(b"PK")

    with pytest.raises(ArcGISUploadError) as exc_info:
        svc.upload_shapefile(zip_path, "SPK001")

    assert "Internal error during object insert." in exc_info.value.detail


@pytest.mark.unit
def test_upload_shapefile_raises_on_empty_features(mocker, tmp_path):
    """Both empty-features variants must raise ArcGISUploadError, not IndexError."""
    svc = _make_service(mocker)
    zip_path = tmp_path / "upload.zip"
    zip_path.write_bytes(b"PK")

    empty_features_body = {
        "featureCollection": {"layers": [{"featureSet": {"features": []}}]}
    }
    mocker.patch("requests.post", return_value=FakeResponse(empty_features_body))
    with pytest.raises(ArcGISUploadError):
        svc.upload_shapefile(zip_path, "SPK001")

    empty_layers_body = {"featureCollection": {"layers": []}}
    mocker.patch("requests.post", return_value=FakeResponse(empty_layers_body))
    with pytest.raises(ArcGISUploadError):
        svc.upload_shapefile(zip_path, "SPK001")


@pytest.mark.unit
def test_upload_shapefile_success_returns_body(mocker, tmp_path):
    """A valid upload response (1 feature) must return the parsed dict without raising."""
    svc = _make_service(mocker)
    zip_path = tmp_path / "upload.zip"
    zip_path.write_bytes(b"PK")

    mocker.patch("requests.post", return_value=FakeResponse(ONE_FEATURE_UPLOAD))
    result = svc.upload_shapefile(zip_path, "SPK001")

    assert result == ONE_FEATURE_UPLOAD


# ---------------------------------------------------------------------------
# apply_edits tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_apply_edits_raises_on_zero_features(mocker):
    """upload_response with no features must raise before posting to applyEdits."""
    svc = _make_service(mocker)
    post_spy = mocker.patch("requests.post")

    empty_upload = {"featureCollection": {"layers": []}}

    with pytest.raises(ArcGISUploadError) as exc_info:
        svc.apply_edits(empty_upload, "SPK001", "KEY001")

    assert "no features" in exc_info.value.detail.lower()
    post_spy.assert_not_called()


@pytest.mark.unit
def test_apply_edits_raises_on_error_body(mocker):
    """applyEdits response body with `error` dict must raise ArcGISUploadError."""
    svc = _make_service(mocker)
    error_body = {"error": {"code": 500, "message": "Server error", "details": []}}
    mocker.patch("requests.post", return_value=FakeResponse(error_body))

    with pytest.raises(ArcGISUploadError):
        svc.apply_edits(ONE_FEATURE_UPLOAD, "SPK001", "KEY001")


@pytest.mark.unit
def test_apply_edits_raises_on_failed_addresult(mocker):
    """A failed addResult entry must raise ArcGISUploadError containing the reason and feature count."""
    svc = _make_service(mocker)
    body = {
        "addResults": [{"success": False, "error": {"description": "dup"}}]
    }
    mocker.patch("requests.post", return_value=FakeResponse(body))

    with pytest.raises(ArcGISUploadError) as exc_info:
        svc.apply_edits(ONE_FEATURE_UPLOAD, "SPK001", "KEY001")

    assert "dup" in exc_info.value.detail
    assert "1" in exc_info.value.detail


@pytest.mark.unit
@pytest.mark.parametrize("error_field", [None, "plain string", {"description": None}])
def test_apply_edits_error_shapes_dont_crash(mocker, error_field):
    """Failed addResults with unusual `error` shapes must raise ArcGISUploadError, not AttributeError."""
    svc = _make_service(mocker)
    result = {"success": False}
    if error_field is not None:
        result["error"] = error_field

    body = {"addResults": [result]}
    mocker.patch("requests.post", return_value=FakeResponse(body))

    with pytest.raises(ArcGISUploadError):
        svc.apply_edits(ONE_FEATURE_UPLOAD, "SPK001", "KEY001")


@pytest.mark.unit
def test_apply_edits_raises_on_empty_addresults(mocker):
    """applyEdits returning empty addResults (0 inserted) must raise ArcGISUploadError."""
    svc = _make_service(mocker)
    body = {"addResults": []}
    mocker.patch("requests.post", return_value=FakeResponse(body))

    with pytest.raises(ArcGISUploadError):
        svc.apply_edits(ONE_FEATURE_UPLOAD, "SPK001", "KEY001")


@pytest.mark.unit
def test_apply_edits_reports_true_inserted_count(mocker):
    """apply_edits must return features_added == count of successful addResults (2)."""
    svc = _make_service(mocker)
    body = {
        "addResults": [
            {"objectId": 1, "success": True},
            {"objectId": 2, "success": True},
        ]
    }
    mocker.patch("requests.post", return_value=FakeResponse(body))

    result = svc.apply_edits(TWO_FEATURE_UPLOAD, "SPK001", "KEY001")

    assert result["features_added"] == 2


# ---------------------------------------------------------------------------
# _raise_on_error unit tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_raise_on_error_handles_nondict_error():
    """_raise_on_error must raise for a plain-string error, and not raise when no error key."""
    with pytest.raises(ArcGISUploadError):
        ArcGISService._raise_on_error({"error": "Token required"}, "Upload")

    # No error key — must not raise
    ArcGISService._raise_on_error({"featureCollection": {}}, "Upload")


# ---------------------------------------------------------------------------
# query_dashboard tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_query_dashboard_still_raises_on_error(mocker):
    """query_dashboard must propagate errors via the refactored _raise_on_error helper."""
    svc = _make_service(mocker)
    error_body = {"error": {"code": 403, "message": "Access denied", "details": []}}
    mocker.patch("requests.get", return_value=FakeResponse(error_body))

    with pytest.raises(ArcGISUploadError) as exc_info:
        svc.query_dashboard("1=1", "Region")

    assert "Access denied" in exc_info.value.detail
