"""VLM (Vision-Language Model) service for document understanding.

Uses Gemma 3 27b via Ollama's OpenAI-compatible API to enhance OCR output,
extract structured information, and correct recognition errors.
"""

from __future__ import annotations

import asyncio
import base64
from pathlib import Path
from typing import Any

import httpx
from loguru import logger

from app.core.config import get_settings


class VLMService:
    """Wraps Gemma 3 27b (via Ollama) for vision-language understanding."""

    def __init__(self) -> None:
        settings = get_settings()
        self._api_base = settings.vlm_api_base.rstrip("/")
        self._model = settings.vlm_model
        self._timeout = settings.vlm_timeout
        self._client: httpx.AsyncClient | None = None

    async def initialize(self) -> None:
        """Create the async HTTP client."""
        self._client = httpx.AsyncClient(timeout=self._timeout)
        logger.info(f"VLM service initialized: model={self._model}, base={self._api_base}")

    async def shutdown(self) -> None:
        if self._client:
            await self._client.aclose()

    async def is_available(self) -> bool:
        """Check if the VLM API endpoint is reachable."""
        try:
            resp = await self._client.get(f"{self._api_base}/models")
            return resp.status_code == 200
        except Exception:
            return False

    async def enhance_document(
        self,
        file_path: Path,
        ocr_text: str,
        output_format: str = "markdown",
    ) -> dict[str, Any]:
        """
        Send the document image + OCR text to VLM for enhanced understanding.

        The VLM corrects OCR errors, structures the content, and produces
        a clean Markdown or JSON output.
        """
        if self._client is None:
            logger.warning("VLM client not initialized")
            return {"enhanced_text": ocr_text, "vlm_used": False}

        # Build the prompt
        if output_format == "json":
            format_instruction = (
                "Output ONLY valid JSON with keys: title, sections (array of "
                "{heading, content}), tables (array of {headers, rows}), metadata."
            )
        else:
            format_instruction = (
                "Output clean, well-structured Markdown. Use proper headings (#, ##), "
                "bullet points, and Markdown tables where appropriate."
            )

        system_prompt = (
            "You are an expert document processing assistant. Your task is to:\n"
            "1. Analyze the document image and the OCR-extracted text below.\n"
            "2. Correct any OCR errors (especially for Chinese characters).\n"
            "3. Reconstruct the document's logical structure.\n"
            f"4. {format_instruction}\n"
            "5. Preserve all original content — do NOT summarize or omit information."
        )

        user_content: list[dict] = []

        # Attach image if it's an image file
        if file_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}:
            img_b64 = await self._encode_image(file_path)
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_b64}"},
            })

        user_content.append({
            "type": "text",
            "text": f"OCR extracted text:\n\n{ocr_text}\n\nPlease process and output the result.",
        })

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.1,
            "max_tokens": 4096,
        }

        try:
            logger.info("Sending document to VLM for enhancement...")
            resp = await self._client.post(
                f"{self._api_base}/chat/completions",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            enhanced = data["choices"][0]["message"]["content"]
            logger.info(f"VLM enhancement complete: {len(enhanced)} chars")
            return {"enhanced_text": enhanced, "vlm_used": True}

        except httpx.TimeoutException:
            logger.warning("VLM request timed out — falling back to OCR text")
            return {"enhanced_text": ocr_text, "vlm_used": False, "error": "timeout"}

        except Exception as exc:
            logger.error(f"VLM request failed: {exc}")
            return {"enhanced_text": ocr_text, "vlm_used": False, "error": str(exc)}

    @staticmethod
    async def _encode_image(path: Path) -> str:
        def _read():
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")

        return await asyncio.to_thread(_read)
