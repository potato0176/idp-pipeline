"""Unit tests for individual services."""

from __future__ import annotations

import pytest

from app.services.chunking_service import ChunkingService
from app.utils.file_handler import get_file_type
from pathlib import Path


class TestChunkingService:
    def test_chunk_plain_text(self, mock_chunking_service: ChunkingService):
        """Should split text into chunks with metadata."""
        text = "Hello world. " * 100  # ~1300 chars
        chunks = mock_chunking_service.chunk_text(text, metadata={"source": "test"})

        assert len(chunks) > 1
        for chunk in chunks:
            assert "text" in chunk
            assert "metadata" in chunk
            assert chunk["metadata"]["source"] == "test"
            assert "chunk_index" in chunk["metadata"]

    def test_chunk_empty_text(self, mock_chunking_service: ChunkingService):
        """Empty text should produce zero chunks."""
        chunks = mock_chunking_service.chunk_text("")
        assert chunks == []

    def test_chunk_markdown(self, mock_chunking_service: ChunkingService):
        """Markdown splitter should preserve header hierarchy."""
        md_text = (
            "# Title\n\nFirst paragraph content here.\n\n"
            "## Section A\n\nSection A content with details.\n\n"
            "## Section B\n\nSection B content with details.\n"
        )
        chunks = mock_chunking_service.chunk_text(
            md_text, use_markdown_splitter=True
        )
        assert len(chunks) >= 1
        # Each chunk should have text
        for chunk in chunks:
            assert len(chunk["text"]) > 0

    def test_chunk_size_respected(self):
        """Chunks should not exceed chunk_size (with some tolerance)."""
        service = ChunkingService(chunk_size=100, chunk_overlap=10)
        text = "A" * 500  # 500 chars
        chunks = service.chunk_text(text)
        for chunk in chunks:
            # Allow small tolerance for split boundaries
            assert len(chunk["text"]) <= 150


class TestFileHandler:
    def test_get_file_type_pdf(self):
        assert get_file_type(Path("doc.pdf")) == "pdf"

    def test_get_file_type_image(self):
        assert get_file_type(Path("scan.png")) == "image"
        assert get_file_type(Path("photo.jpg")) == "image"
        assert get_file_type(Path("scan.tiff")) == "image"


class TestTaskManager:
    @pytest.mark.asyncio
    async def test_task_lifecycle(self, mock_task_manager):
        """Test create → update → complete → get flow."""
        from app.models.schemas import PipelineStage, ProcessingResult, OutputFormat, TaskStatus

        # Create
        task = await mock_task_manager.create_task("test-123")
        assert task.task_id == "test-123"
        assert task.status == TaskStatus.PENDING

        # Update stage
        await mock_task_manager.update_stage("test-123", PipelineStage.OCR, 50.0)
        task = await mock_task_manager.get_task("test-123")
        assert task.current_stage == PipelineStage.OCR
        assert task.progress_pct == 50.0

        # Complete
        result = ProcessingResult(
            output_format=OutputFormat.MARKDOWN,
            content="# Test",
            chunks_count=1,
        )
        await mock_task_manager.complete_task("test-123", result)
        task = await mock_task_manager.get_task("test-123")
        assert task.status == TaskStatus.COMPLETED
        assert task.result is not None

    @pytest.mark.asyncio
    async def test_task_failure(self, mock_task_manager):
        """Test fail_task sets error and status."""
        from app.models.schemas import TaskStatus

        await mock_task_manager.create_task("fail-001")
        await mock_task_manager.fail_task("fail-001", "Something went wrong")

        task = await mock_task_manager.get_task("fail-001")
        assert task.status == TaskStatus.FAILED
        assert task.error == "Something went wrong"

    @pytest.mark.asyncio
    async def test_delete_task(self, mock_task_manager):
        """Deleted tasks should no longer be retrievable."""
        await mock_task_manager.create_task("del-001")
        deleted = await mock_task_manager.delete_task("del-001")
        assert deleted is True
        assert await mock_task_manager.get_task("del-001") is None
