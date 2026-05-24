import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Optional

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import InvalidFileFormatError


class FileUtils:
    @staticmethod
    def create_request_work_dir() -> Path:
        """
        Allocate a fresh per-request work dir under settings.WORK_DIR.
        Caller is responsible for cleanup (e.g. via BackgroundTask).
        """
        root = Path(settings.WORK_DIR)
        root.mkdir(parents=True, exist_ok=True)
        work_dir = root / uuid.uuid4().hex
        work_dir.mkdir()
        return work_dir

    @staticmethod
    async def save_upload_file(
        upload_file: UploadFile, work_dir: Path, filename: Optional[str] = None
    ) -> Path:
        target_name = filename or upload_file.filename
        file_path = work_dir / target_name
        with open(file_path, "wb") as f:
            while chunk := await upload_file.read(1024 * 1024):
                f.write(chunk)
        return file_path

    @staticmethod
    def extract_zip(zip_path: Path, extract_to: Path) -> Path:
        try:
            with zipfile.ZipFile(zip_path, "r") as z:
                # Prevent zip-slip: refuse entries that resolve outside extract_to
                target = extract_to.resolve()
                for member in z.namelist():
                    resolved = (extract_to / member).resolve()
                    if not str(resolved).startswith(str(target)):
                        raise InvalidFileFormatError(f"Unsafe path in archive: {member}")
                z.extractall(extract_to)
            return extract_to
        except zipfile.BadZipFile:
            raise InvalidFileFormatError("Invalid ZIP file")

    @staticmethod
    def validate_file_extension(filename: str, allowed_extensions: list) -> bool:
        ext = Path(filename).suffix.lower()
        return ext in allowed_extensions

    @staticmethod
    def cleanup_dir(path: Path) -> None:
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
