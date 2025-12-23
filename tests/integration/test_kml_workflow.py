import pytest
from fastapi import status

class TestKMLWorkflow:
    def test_generate_shapefile(self, client, sample_kml_zip):
        """Test shapefile generation from KML"""
        with open(sample_kml_zip, 'rb') as f:
            response = client.post(
                "/api/kml/generate-shapefile",
                files={"kml_zip": ("sample.zip", f, "application/zip")},
                data={"spk_number": "SPK123"}
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] == True
        assert data["total_zones"] > 0
        assert "filename" in data
        assert "zone_names" in data

    def test_generate_shapefile_missing_spk(self, client, sample_kml_zip):
        """Test shapefile generation without SPK number"""
        with open(sample_kml_zip, 'rb') as f:
            response = client.post(
                "/api/kml/generate-shapefile",
                files={"kml_zip": ("sample.zip", f, "application/zip")},
                data={}
            )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_process_complete_quick_path(self, client, sample_kml_zip, sample_excel_file):
        """Test complete processing without edited shapefile"""
        with open(sample_kml_zip, 'rb') as kml, open(sample_excel_file, 'rb') as excel:
            response = client.post(
                "/api/kml/process",
                files={
                    "kml_zip": ("zones.zip", kml, "application/zip"),
                    "excel_file": ("data.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                },
                data={
                    "spk_number": "SPK456",
                    "key_id": "KEY789"
                }
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] == True
        assert data["total_zones"] > 0
        assert "filename" in data

    def test_process_with_edited_shapefile(self, client, sample_kml_zip, sample_excel_file, sample_shapefile_zip):
        """Test processing with edited shapefile"""
        with open(sample_kml_zip, 'rb') as kml, \
             open(sample_excel_file, 'rb') as excel, \
             open(sample_shapefile_zip, 'rb') as shp:

            response = client.post(
                "/api/kml/process",
                files={
                    "kml_zip": ("zones.zip", kml, "application/zip"),
                    "excel_file": ("data.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                    "edited_shapefile": ("edited.zip", shp, "application/zip")
                },
                data={
                    "spk_number": "SPK789",
                    "key_id": "KEY123"
                }
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] == True

    def test_process_missing_required_files(self, client, sample_kml_zip):
        """Test processing with missing Excel file"""
        with open(sample_kml_zip, 'rb') as kml:
            response = client.post(
                "/api/kml/process",
                files={
                    "kml_zip": ("zones.zip", kml, "application/zip")
                },
                data={
                    "spk_number": "SPK999",
                    "key_id": "KEY999"
                }
            )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_download_shapefile_for_edit(self, client, sample_kml_zip):
        """Test downloading shapefile for editing"""
        # First generate shapefile
        with open(sample_kml_zip, 'rb') as f:
            client.post(
                "/api/kml/generate-shapefile",
                files={"kml_zip": ("sample.zip", f, "application/zip")},
                data={"spk_number": "SPK111"}
            )

        # Now download it
        response = client.get("/api/kml/download/shapefile-for-edit")

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "application/zip"

    def test_download_final_upload(self, client, sample_kml_zip, sample_excel_file):
        """Test downloading final processed ZIP"""
        # First process files
        with open(sample_kml_zip, 'rb') as kml, open(sample_excel_file, 'rb') as excel:
            client.post(
                "/api/kml/process",
                files={
                    "kml_zip": ("zones.zip", kml, "application/zip"),
                    "excel_file": ("data.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                },
                data={
                    "spk_number": "SPK222",
                    "key_id": "KEY222"
                }
            )

        # Now download it
        response = client.get("/api/kml/download/final-upload")

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "application/zip"
