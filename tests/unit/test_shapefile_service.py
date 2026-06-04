"""Unit tests for ShapefileService.process_excel — header-normalization fix."""
import pytest
import pandas as pd
import geopandas as gpd
from pathlib import Path
from shapely.geometry import LineString
from openpyxl import Workbook

from app.core.exceptions import FileProcessingError
from app.services.shapefile_service import ShapefileService


# ---------------------------------------------------------------------------
# Header constants — single source of truth for both formats
# ---------------------------------------------------------------------------

OLD_HEADERS = [
    "Flight time", "Location", "Aircraft name", "Task Type", "Sprayed area",
    "Total Amount(L/Kg)", "Flight duration(min:sec)", "Crop", "Pliot Name",
    "Team Name", "Field Name", "Serial Number", "Starting Battery Level",
    "Ending Battery Level", "Battery SN",
]

NEW_HEADERS = [
    "Flight time", "Location", "Aircraft name", "Task Type", "Sprayed area",
    "Total Amount(L/Kg)", "Usage Per Mu(L/Kg/Mu)", "Flight duration(min:sec)",
    "Crop", "Pliot Name", "Team Name", "Field Name", "Serial Number",
    "Starting Battery Level", "Ending Battery Level", "Battery SN",
    "Speed", "Height", "Row Spacing", "Body Code", "Plot ID",
]

SERIALS = ["R0000000001", "R0000000002"]
FLIGHT_TIMES = ["2024-01-15 07:30:00 - 07:45:23", "2024-01-15 08:00:00 - 08:12:45"]
TOTAL_AMOUNTS = [1.5, 2.0]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_gdf() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {"Name": SERIALS},
        geometry=[
            LineString([(0, 0), (1, 1)]),
            LineString([(2, 2), (3, 3)]),
        ],
        crs="EPSG:4326",
    )


def _write_xlsx(path: Path, headers: list, rows: list[list]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "flight record"
    ws.append(headers)
    for row in rows:
        ws.append(row)
    wb.save(path)


def _build_row_old(serial: str, flight_time: str, total_amount: float) -> list:
    """Build one data row matching OLD_HEADERS column order."""
    row = [""] * len(OLD_HEADERS)
    row[OLD_HEADERS.index("Serial Number")] = serial
    row[OLD_HEADERS.index("Flight time")] = flight_time
    row[OLD_HEADERS.index("Total Amount(L/Kg)")] = total_amount
    return row


def _build_row_new(
    serial: str, flight_time: str, total_amount: float, usage_per_mu: float
) -> list:
    """Build one data row matching NEW_HEADERS column order."""
    row = [""] * len(NEW_HEADERS)
    row[NEW_HEADERS.index("Serial Number")] = serial
    row[NEW_HEADERS.index("Flight time")] = flight_time
    row[NEW_HEADERS.index("Total Amount(L/Kg)")] = total_amount
    row[NEW_HEADERS.index("Usage Per Mu(L/Kg/Mu)")] = usage_per_mu
    return row


def _old_xlsx(tmp_path: Path, serials=None, flight_times=None, totals=None) -> Path:
    serials = serials or SERIALS
    flight_times = flight_times or FLIGHT_TIMES
    totals = totals or TOTAL_AMOUNTS
    rows = [
        _build_row_old(s, ft, ta)
        for s, ft, ta in zip(serials, flight_times, totals)
    ]
    p = tmp_path / "old_format.xlsx"
    _write_xlsx(p, OLD_HEADERS, rows)
    return p


def _new_xlsx(
    tmp_path: Path,
    serials=None,
    flight_times=None,
    totals=None,
    usage_per_mu=None,
    distractor_field_names=None,
) -> Path:
    serials = serials or SERIALS
    flight_times = flight_times or FLIGHT_TIMES
    totals = totals or TOTAL_AMOUNTS
    usage_per_mu = usage_per_mu or [0.5, 0.7]
    distractor_field_names = distractor_field_names or ["SomeField", "AnotherField"]

    rows = []
    for i, (s, ft, ta, upm) in enumerate(zip(serials, flight_times, totals, usage_per_mu)):
        row = _build_row_new(s, ft, ta, upm)
        if distractor_field_names and i < len(distractor_field_names):
            row[NEW_HEADERS.index("Field Name")] = distractor_field_names[i]
        rows.append(row)

    p = tmp_path / "new_format.xlsx"
    _write_xlsx(p, NEW_HEADERS, rows)
    return p


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_new_format_matches_all_zones(tmp_path):
    """NEW format (21 cols, Serial Number in col M) must match both KML zone names."""
    excel = _new_xlsx(
        tmp_path,
        distractor_field_names=["A430092B00", "A430092B01"],
    )
    filtered, _ = ShapefileService.process_excel(excel, _make_gdf(), "SPK001", "KEY001")

    assert len(filtered) == 2
    assert set(filtered["Name"]) == set(SERIALS)


@pytest.mark.unit
def test_old_format_unchanged(tmp_path):
    """OLD format (15 cols, Serial Number in col L) must still work and produce correct summary values."""
    excel = _old_xlsx(tmp_path)
    _, df_summary = ShapefileService.process_excel(excel, _make_gdf(), "SPK001", "KEY001")

    assert list(df_summary["TaskAmount"]) == [1500.0, 2000.0]

    # StarFlight is [:19] of the flight-time string
    assert list(df_summary["StarFlight"]) == [
        "2024-01-15 07:30:00",
        "2024-01-15 08:00:00",
    ]

    # EndFlight is str(v)[:11] + str(v)[-8:]  (first 11 chars + last 8 chars)
    ft0 = FLIGHT_TIMES[0]
    ft1 = FLIGHT_TIMES[1]
    assert list(df_summary["EndFlight"]) == [
        ft0[:11] + ft0[-8:],
        ft1[:11] + ft1[-8:],
    ]

    assert list(df_summary["Capacity"]) == [25, 25]


@pytest.mark.unit
def test_old_and_new_agree(tmp_path):
    """Both formats with identical serial/flight-time/amount data must produce identical summary frames."""
    (tmp_path / "old").mkdir(parents=True, exist_ok=True)
    old_excel = _old_xlsx(tmp_path / "old")

    (tmp_path / "new").mkdir(parents=True, exist_ok=True)
    new_excel = _new_xlsx(tmp_path / "new")

    _, summary_old = ShapefileService.process_excel(old_excel, _make_gdf(), "SPK001", "KEY001")
    _, summary_new = ShapefileService.process_excel(new_excel, _make_gdf(), "SPK001", "KEY001")

    pd.testing.assert_frame_equal(
        summary_old[["Name", "TaskAmount", "StarFlight", "EndFlight", "Capacity"]].reset_index(drop=True),
        summary_new[["Name", "TaskAmount", "StarFlight", "EndFlight", "Capacity"]].reset_index(drop=True),
    )


@pytest.mark.unit
def test_total_amount_not_confused_with_usage_per_mu(tmp_path):
    """prefix-match on 'total amount' must pick Total Amount(L/Kg), NOT Usage Per Mu(L/Kg/Mu)."""
    # Total amounts: 3.0 / 4.0; usage-per-mu: 99.0 / 99.0 — clearly distinct
    excel = _new_xlsx(
        tmp_path,
        totals=[3.0, 4.0],
        usage_per_mu=[99.0, 99.0],
    )
    _, df_summary = ShapefileService.process_excel(excel, _make_gdf(), "SPK001", "KEY001")

    assert list(df_summary["TaskAmount"]) == [3000.0, 4000.0]


@pytest.mark.unit
def test_zero_matches_raises_422(tmp_path):
    """When no KML zones match Excel serials, FileProcessingError(422) is raised."""
    excel = _old_xlsx(tmp_path, serials=["X9999999999", "X8888888888"])

    with pytest.raises(FileProcessingError) as exc_info:
        ShapefileService.process_excel(excel, _make_gdf(), "SPK001", "KEY001")

    assert exc_info.value.status_code == 422
    assert "match" in exc_info.value.detail.lower()


@pytest.mark.unit
def test_missing_serial_header_raises(tmp_path):
    """Dropping Serial Number header must raise FileProcessingError mentioning the label."""
    broken_headers = [h if h != "Serial Number" else "DRONE_ID" for h in OLD_HEADERS]
    rows = [_build_row_old(s, ft, ta) for s, ft, ta in zip(SERIALS, FLIGHT_TIMES, TOTAL_AMOUNTS)]
    p = tmp_path / "no_serial.xlsx"
    _write_xlsx(p, broken_headers, rows)

    with pytest.raises(FileProcessingError) as exc_info:
        ShapefileService.process_excel(p, _make_gdf(), "SPK001", "KEY001")

    assert "serial number" in exc_info.value.detail.lower()


@pytest.mark.unit
def test_missing_flight_time_header_raises(tmp_path):
    """Dropping Flight time header must raise FileProcessingError mentioning the label."""
    broken_headers = [h if h != "Flight time" else "Timestamp" for h in OLD_HEADERS]
    rows = [_build_row_old(s, ft, ta) for s, ft, ta in zip(SERIALS, FLIGHT_TIMES, TOTAL_AMOUNTS)]
    p = tmp_path / "no_flight_time.xlsx"
    _write_xlsx(p, broken_headers, rows)

    with pytest.raises(FileProcessingError) as exc_info:
        ShapefileService.process_excel(p, _make_gdf(), "SPK001", "KEY001")

    assert "flight time" in exc_info.value.detail.lower()


@pytest.mark.unit
def test_missing_total_amount_header_raises(tmp_path):
    """Dropping Total Amount header must raise FileProcessingError mentioning the label."""
    broken_headers = [h if h != "Total Amount(L/Kg)" else "Volume" for h in OLD_HEADERS]
    rows = [_build_row_old(s, ft, ta) for s, ft, ta in zip(SERIALS, FLIGHT_TIMES, TOTAL_AMOUNTS)]
    p = tmp_path / "no_total_amount.xlsx"
    _write_xlsx(p, broken_headers, rows)

    with pytest.raises(FileProcessingError) as exc_info:
        ShapefileService.process_excel(p, _make_gdf(), "SPK001", "KEY001")

    assert "total amount" in exc_info.value.detail.lower()
