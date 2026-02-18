"""Integration tests for the full IDP pipeline."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from app.services.pipeline import IDPPipeline
from app.services.chunking_service import ChunkingService
from app.utils.task_manager import TaskManager
from app.models.schemas import ProcessRequest, OutputFormat, TaskStatus


@pytest.fixture
def mock_pipeline():
    """Create a pipeline with mocked external services."""
    docling = AsyncMock()
    docling.parse = AsyncMock(return_value={
        "markdown": "# Test Document\n\nThis is test content.",
        "text": "Test Document. This is test content.",
        "metadata": {"source": "test.pdf"},
        "tables": [],
    })

    ocr = AsyncMock()
    ocr.extract_text = AsyncMock(return_value={
        "full_text": "OCR extracted text content here.",
        "blocks": [{"text": "OCR extracted text content here.", "confidence": 0.95}],
        "avg_confidence": 0.95,
    })

    vlm = AsyncMock()
    vlm.enhance_document = AsyncMock(return_value={
        "enhanced_text": "# Test Document\n\nThis is enhanced test content with corrections.",
        "vlm_used": True,
    })

    chunking = ChunkingService(chunk_size=128, chunk_overlap=20)

    vector_store = AsyncMock()
    vector_store.store_chunks = AsyncMock(return_value=["vec-1", "vec-2"])

    task_manager = TaskManager()

    pipeline = IDPPipeline(
        docling=docling,
        ocr=ocr,
        vlm=vlm,
        chunking=chunking,
        vector_store=vector_store,
        task_manager=task_manager,
    )
    return pipeline, task_manager


@pytest.mark.asyncio
async def test_full_pipeline_markdown(mock_pipeline, test_image_file: Path):
    """Full pipeline should produce Markdown output and store vectors."""
    pipeline, tm = mock_pipeline
    task_id = "integ-001"
    await tm.create_task(task_id)

    params = ProcessRequest(
        output_format=OutputFormat.MARKDOWN,
        enable_vlm=True,
        store_in_vectordb=True,
    )

    result = await pipeline.process(task_id, test_image_file, params)

    assert result.output_format == OutputFormat.MARKDOWN
    assert len(result.content) > 0
    assert result.chunks_count > 0
    assert len(result.vector_ids) > 0

    # Task should be completed
    task = await tm.get_task(task_id)
    assert task.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_full_pipeline_json(mock_pipeline, test_image_file: Path):
    """Pipeline with JSON output format."""
    pipeline, tm = mock_pipeline
    task_id = "integ-002"
    await tm.create_task(task_id)

    params = ProcessRequest(
        output_format=OutputFormat.JSON,
        enable_vlm=True,
    )

    result = await pipeline.process(task_id, test_image_file, params)
    assert result.output_format == OutputFormat.JSON

    import json
    parsed = json.loads(result.content)
    assert "content" in parsed


@pytest.mark.asyncio
async def test_pipeline_without_vlm(mock_pipeline, test_image_file: Path):
    """Pipeline should work with VLM disabled."""
    pipeline, tm = mock_pipeline
    task_id = "integ-003"
    await tm.create_task(task_id)

    params = ProcessRequest(enable_vlm=False)

    result = await pipeline.process(task_id, test_image_file, params)
    assert result.metadata.get("vlm_enhanced") is False
    pipeline.vlm.enhance_document.assert_not_called()
