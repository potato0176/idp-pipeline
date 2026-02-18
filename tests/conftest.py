"""Shared pytest fixtures for the IDP Pipeline test suite."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from PIL import Image

# Set test environment before importing app
os.environ["APP_ENV"] = "test"
os.environ["DEBUG"] = "false"
os.environ["OCR_GPU"] = "false"
os.environ["UPLOAD_DIR"] = "/tmp/idp_test_uploads"
os.environ["OUTPUT_DIR"] = "/tmp/idp_test_outputs"
os.environ["CHROMA_PERSIST_DIR"] = "/tmp/idp_test_chroma"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_image_bytes() -> bytes:
    """Create a simple test PNG image with text-like content."""
    img = Image.new("RGB", (200, 100), color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


@pytest.fixture
def test_image_file(tmp_path: Path, test_image_bytes: bytes) -> Path:
    """Save a test image to disk."""
    path = tmp_path / "test_document.png"
    path.write_bytes(test_image_bytes)
    return path


@pytest.fixture
def test_pdf_bytes() -> bytes:
    """Create a minimal valid PDF."""
    # Minimal valid PDF structure
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\n"
        b"startxref\n206\n%%EOF"
    )
    return pdf_content


@pytest.fixture
def mock_task_manager():
    """Create a mock TaskManager."""
    from app.utils.task_manager import TaskManager
    return TaskManager()


@pytest.fixture
def mock_chunking_service():
    """Create a real ChunkingService for testing."""
    from app.services.chunking_service import ChunkingService
    return ChunkingService(chunk_size=128, chunk_overlap=20)
