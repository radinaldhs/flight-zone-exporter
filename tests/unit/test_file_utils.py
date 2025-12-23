import pytest
from app.utils.file_utils import FileUtils
from app.core.exceptions import InvalidFileFormatError
from pathlib import Path
import zipfile

class TestFileUtils:
    def test_validate_file_extension_valid(self):
        """Test valid file extension"""
        assert FileUtils.validate_file_extension("file.zip", [".zip"]) == True
        assert FileUtils.validate_file_extension("data.xlsx", [".xlsx", ".xls"]) == True

    def test_validate_file_extension_invalid(self):
        """Test invalid file extension returns False"""
        result = FileUtils.validate_file_extension("file.txt", [".zip"])
        assert result == False

    def test_extract_zip_valid(self, temp_work_dir, sample_kml_zip):
        """Test ZIP extraction"""
        extract_path = temp_work_dir / "extracted"
        FileUtils.extract_zip(sample_kml_zip, extract_path)

        assert extract_path.exists()
        assert len(list(extract_path.glob("*.kml"))) > 0

    def test_extract_zip_invalid(self, temp_work_dir):
        """Test invalid ZIP raises error"""
        fake_zip = temp_work_dir / "fake.zip"
        fake_zip.write_text("not a zip file")

        with pytest.raises(InvalidFileFormatError, match="Invalid ZIP file"):
            FileUtils.extract_zip(fake_zip, temp_work_dir / "out")

    def test_get_work_dir(self, temp_work_dir):
        """Test working directory creation"""
        work_dir = FileUtils.get_work_dir()
        assert work_dir.exists()
        assert work_dir.is_dir()

    def test_cleanup_work_dir(self, temp_work_dir):
        """Test working directory cleanup"""
        # Create some test files
        test_file = temp_work_dir / "test.txt"
        test_file.write_text("test content")

        FileUtils.cleanup_work_dir(temp_work_dir)
        assert not temp_work_dir.exists()
