"""File upload and temporary storage utilities."""

from __future__ import annotations

import uuid
import shutil
from pathlib import Path

import aiofiles
from fastapi import UploadFile
from loguru import logger

from app.core.config import get_settings

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"}


async def save_upload(file: UploadFile) -> Path:
    """
    Save an uploaded file to the configured upload directory.

    Returns the Path of the saved file.
    Raises ValueError for unsupported file types or oversized files.
    """
    settings = get_settings()

    # Validate extension
    suffix = Path(file.filename or "unknown").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{suffix}'. "
            f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # Generate unique filename
    unique_name = f"{uuid.uuid4().hex}{suffix}"
    dest = Path(settings.upload_dir) / unique_name
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Stream-write to disk (memory-efficient for large files)
    total_bytes = 0
    max_bytes = settings.max_file_size_mb * 1024 * 1024

    async with aiofiles.open(dest, "wb") as out:
        while chunk := await file.read(1024 * 256):  # 256 KB chunks
            total_bytes += len(chunk)
            if total_bytes > max_bytes:
                dest.unlink(missing_ok=True)
                raise ValueError(
                    f"File exceeds maximum size of {settings.max_file_size_mb} MB"
                )
            await out.write(chunk)

    logger.info(f"Saved upload: {file.filename} → {dest} ({total_bytes / 1024:.1f} KB)")
    return dest


def cleanup_file(path: Path) -> None:
    """Remove a temporary file if it exists."""
    try:
        if path.exists():
            path.unlink()
            logger.debug(f"Cleaned up: {path}")
    except OSError as exc:
        logger.warning(f"Failed to clean up {path}: {exc}")


def get_file_type(path: Path) -> str:
    """Return 'pdf' or 'image' based on file extension."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    return "image"
