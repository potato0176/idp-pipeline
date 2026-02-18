"""Pipeline orchestrator — coordinates all services in the IDP flow.

Flow:  Upload → Docling Parse → OCR → VLM Enhance → Chunk → Vector Store → Save to Disk
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loguru import logger

from app.models.schemas import (
    OutputFormat,
    PipelineStage,
    ProcessingResult,
    ProcessRequest,
)
from app.services.docling_parser import DoclingParser
from app.services.ocr_service import OCRService
from app.services.vlm_service import VLMService
from app.services.chunking_service import ChunkingService
from app.services.vector_store import VectorStoreService
from app.utils.file_handler import get_file_type
from app.utils.task_manager import TaskManager
from app.core.config import get_settings


class IDPPipeline:
    """Main orchestrator that wires all services together."""

    def __init__(
        self,
        docling: DoclingParser,
        ocr: OCRService,
        vlm: VLMService,
        chunking: ChunkingService,
        vector_store: VectorStoreService,
        task_manager: TaskManager,
    ) -> None:
        self.docling = docling
        self.ocr = ocr
        self.vlm = vlm
        self.chunking = chunking
        self.vector_store = vector_store
        self.task_manager = task_manager

    async def process(
        self,
        task_id: str,
        file_path: Path,
        params: ProcessRequest,
    ) -> ProcessingResult:
        """
        Run the full IDP pipeline on an uploaded file.

        This method is designed to be launched as a background task.
        It updates the TaskManager at each stage so clients can poll progress.
        """
        file_type = get_file_type(file_path)
        combined_text = ""
        metadata: dict[str, Any] = {"source": file_path.name, "file_type": file_type}

        try:
            # ── Stage 1: Docling Parse (PDF only) ─────────────────────
            await self.task_manager.update_stage(task_id, PipelineStage.DOCLING_PARSE, 10)

            docling_result: dict[str, Any] = {"markdown": "", "text": ""}
            if file_type == "pdf":
                docling_result = await self.docling.parse(file_path)
                combined_text = docling_result.get("markdown") or docling_result.get("text", "")
                metadata["docling_tables"] = len(docling_result.get("tables", []))

            # ── Stage 2: OCR ──────────────────────────────────────────
            await self.task_manager.update_stage(task_id, PipelineStage.OCR, 30)

            ocr_result = await self.ocr.extract_text(file_path)
            ocr_text = ocr_result.get("full_text", "")
            metadata["ocr_confidence"] = ocr_result.get("avg_confidence", 0.0)
            metadata["ocr_blocks"] = len(ocr_result.get("blocks", []))

            # Merge: prefer Docling output for PDFs, supplement with OCR
            if combined_text and ocr_text:
                if len(ocr_text) > len(combined_text) * 0.3:
                    combined_text += f"\n\n---\n\n{ocr_text}"
            elif not combined_text:
                combined_text = ocr_text

            # ── Stage 3: VLM Enhancement (optional) ───────────────────
            await self.task_manager.update_stage(task_id, PipelineStage.VLM_ENHANCE, 50)

            if params.enable_vlm and combined_text:
                vlm_result = await self.vlm.enhance_document(
                    file_path=file_path,
                    ocr_text=combined_text,
                    output_format=params.output_format.value,
                )
                if vlm_result.get("vlm_used"):
                    combined_text = vlm_result["enhanced_text"]
                    metadata["vlm_enhanced"] = True
                else:
                    metadata["vlm_enhanced"] = False
                    if vlm_result.get("error"):
                        metadata["vlm_error"] = vlm_result["error"]
            else:
                metadata["vlm_enhanced"] = False

            # ── Stage 4: Chunking ─────────────────────────────────────
            await self.task_manager.update_stage(task_id, PipelineStage.CHUNKING, 70)

            use_md = params.output_format == OutputFormat.MARKDOWN
            chunks = self.chunking.chunk_text(
                text=combined_text,
                metadata={"source": file_path.name},
                use_markdown_splitter=use_md,
            )

            # ── Stage 5: Vector Store ─────────────────────────────────
            await self.task_manager.update_stage(task_id, PipelineStage.VECTOR_STORE, 85)

            vector_ids: list[str] = []
            if params.store_in_vectordb and chunks:
                vector_ids = await self.vector_store.store_chunks(
                    chunks=chunks,
                    source_file=file_path.name,
                )

            # ── Build final result ────────────────────────────────────
            if params.output_format == OutputFormat.JSON:
                content = json.dumps(
                    {
                        "content": combined_text,
                        "metadata": metadata,
                        "chunks_count": len(chunks),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            else:
                content = combined_text

            result = ProcessingResult(
                output_format=params.output_format,
                content=content,
                metadata=metadata,
                chunks_count=len(chunks),
                vector_ids=vector_ids,
            )

            # ── Stage 6: Save result to disk ──────────────────────────
            output_path = self._save_result(task_id, file_path.stem, result)
            result.metadata["output_file"] = str(output_path)

            await self.task_manager.complete_task(task_id, result)
            logger.info(
                f"Pipeline complete for task {task_id}: "
                f"{len(chunks)} chunks stored, output saved to {output_path}"
            )
            return result

        except Exception as exc:
            error_msg = f"Pipeline error: {exc}"
            logger.error(error_msg)
            await self.task_manager.fail_task(task_id, error_msg)
            raise

    def _save_result(self, task_id: str, source_name: str, result: ProcessingResult) -> Path:
        """Save the processing result to the output directory."""
        settings = get_settings()
        output_dir = Path(settings.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Determine file extension
        ext = "json" if result.output_format == OutputFormat.JSON else "md"
        filename = f"{source_name}_{task_id[:8]}.{ext}"
        output_path = output_dir / filename

        output_path.write_text(result.content, encoding="utf-8")
        logger.info(f"Result saved: {output_path}")

        # Also save metadata
        meta_path = output_dir / f"{source_name}_{task_id[:8]}_meta.json"
        meta_path.write_text(
            json.dumps(result.metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return output_path