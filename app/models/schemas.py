"""Pydantic schemas for API requests and responses."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────
class OutputFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineStage(str, Enum):
    UPLOAD = "upload"
    DOCLING_PARSE = "docling_parse"
    OCR = "ocr"
    VLM_ENHANCE = "vlm_enhance"
    CHUNKING = "chunking"
    VECTOR_STORE = "vector_store"
    DONE = "done"


# ──────────────────────────────────────────────
# Request Models
# ──────────────────────────────────────────────
class ProcessRequest(BaseModel):
    """Parameters sent alongside file upload."""
    output_format: OutputFormat = OutputFormat.MARKDOWN
    languages: list[str] = Field(default_factory=lambda: ["ch_tra", "en"])
    enable_vlm: bool = True
    chunk_size: int = 512
    chunk_overlap: int = 50
    store_in_vectordb: bool = True


class SearchRequest(BaseModel):
    """Semantic search query."""
    query: str
    top_k: int = Field(default=5, ge=1, le=50)
    collection_name: str | None = None


# ──────────────────────────────────────────────
# Response Models
# ──────────────────────────────────────────────
class TaskResponse(BaseModel):
    """Returned when a processing task is created."""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatus = TaskStatus.PENDING
    message: str = "Task created successfully"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TaskStatusResponse(BaseModel):
    """Full status of a processing task."""
    task_id: str
    status: TaskStatus
    current_stage: PipelineStage | None = None
    progress_pct: float = 0.0
    result: ProcessingResult | None = None
    error: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class ProcessingResult(BaseModel):
    """Result payload of a completed task."""
    output_format: OutputFormat
    content: str  # Markdown string or JSON string
    metadata: dict[str, Any] = Field(default_factory=dict)
    chunks_count: int = 0
    vector_ids: list[str] = Field(default_factory=list)


class SearchResult(BaseModel):
    """Single search hit."""
    chunk_text: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Collection of search results."""
    query: str
    results: list[SearchResult]
    total: int


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    services: dict[str, bool] = Field(default_factory=dict)
    version: str = "1.0.0"


# Rebuild forward refs
TaskStatusResponse.model_rebuild()
