"""EasyOCR service for optical character recognition.

Supports multi-language OCR including Traditional Chinese and English.
Runs inference in a thread pool to avoid blocking the event loop.
"""

from __future__ import annotations

import asyncio
import base64
from pathlib import Path
from typing import Any

from loguru import logger
from PIL import Image


class OCRService:
    """Wraps EasyOCR for async OCR processing."""

    def __init__(self, languages: list[str] | None = None, gpu: bool = True) -> None:
        self._languages = languages or ["ch_tra", "en"]
        self._gpu = gpu
        self._reader = None

    async def initialize(self) -> None:
        """Lazy-load the EasyOCR reader (downloads models on first run)."""
        def _load():
            try:
                import easyocr
                self._reader = easyocr.Reader(self._languages, gpu=self._gpu)
                logger.info(f"EasyOCR initialized: languages={self._languages}, gpu={self._gpu}")
            except ImportError:
                logger.warning("EasyOCR not installed. Install with: pip install easyocr")

        await asyncio.to_thread(_load)

    async def extract_text(self, file_path: Path) -> dict[str, Any]:
        """
        Run OCR on an image or each page of a PDF.

        Returns:
            dict with keys:
                - "full_text": str
                - "blocks": list[dict]  (each with text, confidence, bbox)
                - "avg_confidence": float
        """
        if self._reader is None:
            logger.warning("EasyOCR not available — returning empty OCR result")
            return {"full_text": "", "blocks": [], "avg_confidence": 0.0}

        logger.info(f"OCR processing: {file_path.name}")

        file_type = file_path.suffix.lower()

        if file_type == ".pdf":
            return await self._ocr_pdf(file_path)
        else:
            return await self._ocr_image(file_path)

    async def _ocr_image(self, image_path: Path) -> dict[str, Any]:
        """OCR a single image file."""
        def _run():
            results = self._reader.readtext(str(image_path))
            return self._format_results(results)

        return await asyncio.to_thread(_run)

    async def _ocr_pdf(self, pdf_path: Path) -> dict[str, Any]:
        """Convert PDF pages to images, then OCR each page."""
        def _run():
            try:
                from pdf2image import convert_from_path
                images = convert_from_path(str(pdf_path), dpi=300)
            except ImportError:
                logger.warning("pdf2image not installed — cannot OCR PDF pages")
                return {"full_text": "", "blocks": [], "avg_confidence": 0.0}
            except Exception as exc:
                logger.error(f"PDF to image conversion failed: {exc}")
                return {"full_text": "", "blocks": [], "avg_confidence": 0.0}

            all_blocks: list[dict] = []
            for page_num, img in enumerate(images, 1):
                import numpy as np
                img_array = np.array(img)
                results = self._reader.readtext(img_array)
                for bbox, text, conf in results:
                    all_blocks.append({
                        "text": text,
                        "confidence": float(conf),
                        "bbox": [[float(c) for c in point] for point in bbox],
                        "page": page_num,
                    })

            full_text = "\n".join(b["text"] for b in all_blocks)
            avg_conf = (
                sum(b["confidence"] for b in all_blocks) / len(all_blocks)
                if all_blocks
                else 0.0
            )
            return {
                "full_text": full_text,
                "blocks": all_blocks,
                "avg_confidence": avg_conf,
            }

        return await asyncio.to_thread(_run)

    @staticmethod
    def _format_results(results: list) -> dict[str, Any]:
        """Format raw EasyOCR output into a structured dict."""
        blocks: list[dict] = []
        for bbox, text, conf in results:
            blocks.append({
                "text": text,
                "confidence": float(conf),
                "bbox": [[float(c) for c in point] for point in bbox],
            })

        full_text = "\n".join(b["text"] for b in blocks)
        avg_conf = sum(b["confidence"] for b in blocks) / len(blocks) if blocks else 0.0

        return {
            "full_text": full_text,
            "blocks": blocks,
            "avg_confidence": avg_conf,
        }

    async def image_to_base64(self, file_path: Path) -> str:
        """Convert image file to base64 string (used by VLM service)."""
        def _encode():
            with open(file_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")

        return await asyncio.to_thread(_encode)
