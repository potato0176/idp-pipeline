"""API route definitions for the IDP Pipeline."""

from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from loguru import logger

from app.models.schemas import (
    HealthResponse,
    OutputFormat,
    ProcessRequest,
    SearchRequest,
    SearchResponse,
    SearchResult,
    TaskResponse,
    TaskStatusResponse,
)
from app.api.dependencies import (
    get_pipeline,
    get_task_manager,
    get_vector_store,
)
from app.services.pipeline import IDPPipeline
from app.services.vector_store import VectorStoreService
from app.utils.file_handler import save_upload
from app.utils.task_manager import TaskManager

router = APIRouter(prefix="/api/v1", tags=["IDP Pipeline"])


# ──────────────────────────────────────────────
# POST /process — Upload & Start Processing
# ──────────────────────────────────────────────
@router.post("/process", response_model=TaskResponse, status_code=202)
async def process_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF or image file to process"),
    output_format: str = Form("markdown"),
    languages: str = Form("ch_tra,en"),
    enable_vlm: bool = Form(True),
    chunk_size: int = Form(512),
    chunk_overlap: int = Form(50),
    store_in_vectordb: bool = Form(True),
):
    """
    Upload a document (PDF or image) and start the async IDP pipeline.

    Returns a `task_id` immediately. Use `GET /tasks/{task_id}` to poll status.
    """
    # Validate output format
    try:
        fmt = OutputFormat(output_format)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid output_format. Choose from: {[e.value for e in OutputFormat]}",
        )

    # Save uploaded file
    try:
        file_path = await save_upload(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Build request params
    params = ProcessRequest(
        output_format=fmt,
        languages=[l.strip() for l in languages.split(",")],
        enable_vlm=enable_vlm,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        store_in_vectordb=store_in_vectordb,
    )

    # Create task
    task_id = str(uuid.uuid4())
    tm = get_task_manager()
    await tm.create_task(task_id)

    # Launch pipeline as background task
    pipeline = get_pipeline()
    background_tasks.add_task(pipeline.process, task_id, file_path, params)

    logger.info(f"Task {task_id} queued for {file.filename}")
    return TaskResponse(task_id=task_id, message=f"Processing started for '{file.filename}'")


# ──────────────────────────────────────────────
# GET /tasks/{task_id} — Poll Task Status
# ──────────────────────────────────────────────
@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Retrieve the current status and result of a processing task."""
    tm = get_task_manager()
    task = await tm.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return task


# ──────────────────────────────────────────────
# GET /tasks/{task_id}/download — Download Result
# ──────────────────────────────────────────────
@router.get("/tasks/{task_id}/download")
async def download_result(task_id: str):
    """Download the processed output (Markdown or JSON)."""
    from fastapi.responses import PlainTextResponse

    tm = get_task_manager()
    task = await tm.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    if task.result is None:
        raise HTTPException(status_code=400, detail="Task not yet completed")

    content_type = (
        "application/json"
        if task.result.output_format == OutputFormat.JSON
        else "text/markdown"
    )
    extension = "json" if task.result.output_format == OutputFormat.JSON else "md"

    return PlainTextResponse(
        content=task.result.content,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="result_{task_id[:8]}.{extension}"'
        },
    )


# ──────────────────────────────────────────────
# DELETE /tasks/{task_id} — Remove Task
# ──────────────────────────────────────────────
@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """Delete a task and its associated data."""
    tm = get_task_manager()
    deleted = await tm.delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return {"message": f"Task '{task_id}' deleted"}


# ──────────────────────────────────────────────
# POST /search — Semantic Search
# ──────────────────────────────────────────────
@router.post("/search", response_model=SearchResponse)
async def semantic_search(request: SearchRequest):
    """Search the vector database for relevant document chunks."""
    vs = get_vector_store()

    if not await vs.is_available():
        raise HTTPException(status_code=503, detail="Vector store not available")

    hits = await vs.search(
        query=request.query,
        top_k=request.top_k,
        collection_name=request.collection_name,
    )

    results = [
        SearchResult(
            chunk_text=h["text"],
            score=h["score"],
            metadata=h.get("metadata", {}),
        )
        for h in hits
    ]

    return SearchResponse(query=request.query, results=results, total=len(results))


# ──────────────────────────────────────────────
# GET /health — Health Check
# ──────────────────────────────────────────────
@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check the health of all pipeline services."""
    from app.api.dependencies import vlm_service, vector_store_service, ocr_service

    vlm_ok = await vlm_service.is_available()
    vs_ok = await vector_store_service.is_available()

    return HealthResponse(
        status="healthy" if vs_ok else "degraded",
        services={
            "docling": True,  # Always available (fallback mode)
            "ocr": ocr_service is not None,
            "vlm": vlm_ok,
            "vector_store": vs_ok,
        },
    )
