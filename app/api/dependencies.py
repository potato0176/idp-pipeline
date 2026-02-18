"""FastAPI dependency injection — provides service instances to route handlers."""

from __future__ import annotations

from app.services.docling_parser import DoclingParser
from app.services.ocr_service import OCRService
from app.services.vlm_service import VLMService
from app.services.chunking_service import ChunkingService
from app.services.vector_store import VectorStoreService
from app.services.pipeline import IDPPipeline
from app.utils.task_manager import TaskManager
from app.core.config import get_settings

# ── Singletons (created at import time, initialized in app lifespan) ──
task_manager = TaskManager()
docling_parser = DoclingParser()
ocr_service: OCRService | None = None
vlm_service = VLMService()
chunking_service: ChunkingService | None = None
vector_store_service = VectorStoreService()
pipeline: IDPPipeline | None = None


async def init_services() -> None:
    """Initialize all services — called during FastAPI lifespan startup."""
    global ocr_service, chunking_service, pipeline

    settings = get_settings()
    settings.ensure_directories()

    # Initialize each service
    await docling_parser.initialize()

    ocr_service = OCRService(
        languages=settings.ocr_language_list,
        gpu=settings.ocr_gpu,
    )
    await ocr_service.initialize()

    await vlm_service.initialize()

    chunking_service = ChunkingService(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    await vector_store_service.initialize()

    # Wire up the pipeline orchestrator
    pipeline = IDPPipeline(
        docling=docling_parser,
        ocr=ocr_service,
        vlm=vlm_service,
        chunking=chunking_service,
        vector_store=vector_store_service,
        task_manager=task_manager,
    )


async def shutdown_services() -> None:
    """Cleanup on shutdown."""
    await vlm_service.shutdown()


def get_pipeline() -> IDPPipeline:
    assert pipeline is not None, "Pipeline not initialized"
    return pipeline


def get_task_manager() -> TaskManager:
    return task_manager


def get_vector_store() -> VectorStoreService:
    return vector_store_service
