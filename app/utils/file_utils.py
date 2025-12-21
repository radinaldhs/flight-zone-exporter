import shutil
import zipfile
from pathlib import Path
from typing import Optional
from fastapi import UploadFile
import tempfile

from app.core.config import settings
from app.core.exceptions import InvalidFileFormatError


class FileUtils:
    @staticmethod
    def get_work_dir() -> Path:
        work_dir = Path(settings.WORK_DIR)
        if work_dir.exists():
            shutil.rmtree(work_dir)
        work_dir.mkdir(parents=True)
        return work_dir

    @staticmethod
    async def save_upload_file(upload_file: UploadFile, work_dir: Path, filename: Optional[str] = None) -> Path:
        if not filename:
            filename = upload_file.filename

        file_path = work_dir / filename
        with open(file_path, "wb") as f:
            content = await upload_file.read()
            f.write(content)

        return file_path

    @staticmethod
    def extract_zip(zip_path: Path, extract_to: Path) -> Path:
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(extract_to)
            return extract_to
        except zipfile.BadZipFile:
            raise InvalidFileFormatError("Invalid ZIP file")

    @staticmethod
    def validate_file_extension(filename: str, allowed_extensions: list) -> bool:
        ext = Path(filename).suffix.lower()
        return ext in allowed_extensions

    @staticmethod
    def cleanup_work_dir(work_dir: Path):
        if work_dir.exists():
            shutil.rmtree(work_dir)
