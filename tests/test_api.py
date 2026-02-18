"""Tests for API endpoints."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from io import BytesIO

from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client with mocked services."""
    with patch("app.api.dependencies.init_services", new_callable=AsyncMock), \
         patch("app.api.dependencies.shutdown_services", new_callable=AsyncMock):
        from app.main import app
        with TestClient(app) as c:
            yield c


class TestHealthEndpoint:
    def test_health_check(self, client):
        """Health endpoint should return 200."""
        with patch("app.api.dependencies.vlm_service") as mock_vlm, \
             patch("app.api.dependencies.vector_store_service") as mock_vs, \
             patch("app.api.dependencies.ocr_service", MagicMock()):
            mock_vlm.is_available = AsyncMock(return_value=True)
            mock_vs.is_available = AsyncMock(return_value=True)

            resp = client.get("/api/v1/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] in ("healthy", "degraded")
            assert "services" in data


class TestProcessEndpoint:
    def test_upload_unsupported_format(self, client):
        """Uploading a .txt file should return 400."""
        file_content = b"hello world"
        resp = client.post(
            "/api/v1/process",
            files={"file": ("test.txt", BytesIO(file_content), "text/plain")},
        )
        assert resp.status_code == 400

    def test_upload_valid_image(self, client, test_image_bytes):
        """Uploading a valid PNG should return 202 with task_id."""
        with patch("app.api.routes.get_pipeline") as mock_get_pipe, \
             patch("app.api.routes.get_task_manager") as mock_get_tm:

            mock_tm = AsyncMock()
            mock_tm.create_task = AsyncMock(return_value=MagicMock())
            mock_get_tm.return_value = mock_tm

            mock_pipe = MagicMock()
            mock_get_pipe.return_value = mock_pipe

            resp = client.post(
                "/api/v1/process",
                files={"file": ("scan.png", BytesIO(test_image_bytes), "image/png")},
                data={"output_format": "markdown"},
            )
            assert resp.status_code == 202
            data = resp.json()
            assert "task_id" in data


class TestTaskEndpoint:
    def test_task_not_found(self, client):
        """Querying a non-existent task should return 404."""
        with patch("app.api.routes.get_task_manager") as mock_get_tm:
            mock_tm = AsyncMock()
            mock_tm.get_task = AsyncMock(return_value=None)
            mock_get_tm.return_value = mock_tm

            resp = client.get("/api/v1/tasks/nonexistent-id")
            assert resp.status_code == 404


class TestSearchEndpoint:
    def test_search_vector_store_unavailable(self, client):
        """Search when vector store is down should return 503."""
        with patch("app.api.routes.get_vector_store") as mock_get_vs:
            mock_vs = AsyncMock()
            mock_vs.is_available = AsyncMock(return_value=False)
            mock_get_vs.return_value = mock_vs

            resp = client.post(
                "/api/v1/search",
                json={"query": "test query", "top_k": 5},
            )
            assert resp.status_code == 503