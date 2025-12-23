import pytest
from app.services.kml_parser import KMLParser
from app.core.exceptions import FileProcessingError
from pathlib import Path

class TestKMLParser:
    def test_parse_valid_kml(self, temp_work_dir, sample_kml_file):
        """Test parsing valid KML file"""
        # KMLParser.parse_kmls expects a folder, so create one with the KML
        kml_dir = temp_work_dir / "kml_folder"
        kml_dir.mkdir()
        import shutil
        shutil.copy(sample_kml_file, kml_dir / "sample.kml")

        gdf = KMLParser.parse_kmls(kml_dir)

        assert len(gdf) > 0
        assert 'Name' in gdf.columns
        assert 'geometry' in gdf.columns
        # Check first zone data
        assert gdf.iloc[0]['Name'] == 'Zone_001'
        assert gdf.iloc[0]['Flight_Con'] == 'DRONE_001'
        assert gdf.iloc[0]['Height'] == 50

    def test_parse_multiple_zones(self, temp_work_dir, sample_kml_file):
        """Test parsing KML with multiple zones"""
        kml_dir = temp_work_dir / "kml_folder"
        kml_dir.mkdir()
        import shutil
        shutil.copy(sample_kml_file, kml_dir / "sample.kml")

        gdf = KMLParser.parse_kmls(kml_dir)

        assert len(gdf) == 2
        assert gdf.iloc[0]['Name'] == 'Zone_001'
        assert gdf.iloc[1]['Name'] == 'Zone_002'

    def test_parse_kml_no_placemarks(self, temp_work_dir):
        """Test KML with no placemarks raises error"""
        kml_dir = temp_work_dir / "empty_kml"
        kml_dir.mkdir()
        kml_no_placemarks = kml_dir / "empty.kml"
        kml_no_placemarks.write_text("""<?xml version="1.0" encoding="UTF-8"?>
        <kml xmlns="http://www.opengis.net/kml/2.2">
            <Document></Document>
        </kml>""")

        with pytest.raises(FileProcessingError, match="No valid placemarks"):
            KMLParser.parse_kmls(kml_dir)

    def test_parse_invalid_xml(self, temp_work_dir):
        """Test invalid XML raises error"""
        kml_dir = temp_work_dir / "invalid_kml"
        kml_dir.mkdir()
        invalid_kml = kml_dir / "invalid.kml"
        invalid_kml.write_text("not valid xml")

        with pytest.raises(FileProcessingError):
            KMLParser.parse_kmls(kml_dir)

    def test_parse_kml_missing_coordinates(self, temp_work_dir):
        """Test KML with missing coordinates"""
        kml_dir = temp_work_dir / "no_coords_kml"
        kml_dir.mkdir()
        kml_no_coords = kml_dir / "no_coords.kml"
        kml_no_coords.write_text("""<?xml version="1.0" encoding="UTF-8"?>
        <kml xmlns="http://www.opengis.net/kml/2.2">
            <Document>
                <Placemark>
                    <name>Zone_001</name>
                    <LineString></LineString>
                </Placemark>
            </Document>
        </kml>""")

        # Should handle gracefully or raise specific error
        with pytest.raises(FileProcessingError, match="No valid placemarks"):
            KMLParser.parse_kmls(kml_dir)

    def test_parse_kml_extended_data(self, temp_work_dir, sample_kml_file):
        """Test parsing extended data from KML"""
        kml_dir = temp_work_dir / "kml_folder"
        kml_dir.mkdir()
        import shutil
        shutil.copy(sample_kml_file, kml_dir / "sample.kml")

        gdf = KMLParser.parse_kmls(kml_dir)

        # Check all extended data fields are parsed
        assert 'Flight_Con' in gdf.columns
        assert 'Height' in gdf.columns
        assert 'Route_Spacing' in gdf.columns
        assert 'Task_Flight_Speed' in gdf.columns
        assert 'Task_Area' in gdf.columns
        assert 'Flight_Time' in gdf.columns
        assert 'Spray_amount' in gdf.columns
