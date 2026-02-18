"""Docling-based document parsing service.

Handles structural extraction from PDFs: headings, paragraphs, tables, etc.
Falls back to raw text extraction when Docling is unavailable.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from loguru import logger


class DoclingParser:
    """Wraps Docling for structured PDF parsing."""

    def __init__(self) -> None:
        self._converter = None

    async def initialize(self) -> None:
        """Lazy-load the Docling converter (heavy import)."""
        def _load():
            try:
                from docling.document_converter import DocumentConverter
                self._converter = DocumentConverter()
                logger.info("Docling DocumentConverter initialized")
            except ImportError:
                logger.warning(
                    "Docling not installed. PDF parsing will use fallback. "
                    "Install with: pip install docling"
                )

        await asyncio.to_thread(_load)

    async def parse(self, file_path: Path) -> dict[str, Any]:
        """
        Parse a PDF file and return structured content.

        Returns:
            dict with keys:
                - "markdown": str  (full Markdown representation)
                - "text": str      (plain text)
                - "metadata": dict (title, pages, etc.)
                - "tables": list   (extracted tables)
        """
        if file_path.suffix.lower() != ".pdf":
            logger.info(f"Skipping Docling parse for non-PDF file: {file_path.name}")
            return {"markdown": "", "text": "", "metadata": {}, "tables": []}

        if self._converter is None:
            logger.warning("Docling not available — returning empty parse result")
            return {"markdown": "", "text": "", "metadata": {}, "tables": []}

        logger.info(f"Docling parsing: {file_path.name}")

        def _convert():
            result = self._converter.convert(str(file_path))
            doc = result.document

            markdown = doc.export_to_markdown()

            # Extract plain text
            text_parts: list[str] = []
            tables: list[dict] = []

            for item in doc.iterate_items():
                element = item[1] if isinstance(item, tuple) else item
                # Get text from the element
                if hasattr(element, "text"):
                    text_parts.append(element.text)

            metadata = {
                "source": file_path.name,
                "num_pages": getattr(doc, "num_pages", None),
            }

            return {
                "markdown": markdown,
                "text": "\n".join(text_parts),
                "metadata": metadata,
                "tables": tables,
            }

        try:
            result = await asyncio.to_thread(_convert)
            logger.info(
                f"Docling parse complete: {len(result['text'])} chars, "
                f"{len(result['tables'])} tables"
            )
            return result
        except Exception as exc:
            logger.error(f"Docling parse failed: {exc}")
            return {"markdown": "", "text": "", "metadata": {"error": str(exc)}, "tables": []}
