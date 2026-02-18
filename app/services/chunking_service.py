"""Text chunking service using LangChain text splitters.

Splits processed document text into overlapping chunks suitable for
vector embedding and semantic search.
"""

from __future__ import annotations

from typing import Any

from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    MarkdownHeaderTextSplitter,
)
from loguru import logger


class ChunkingService:
    """Handles intelligent text splitting for vector storage."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50) -> None:
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

        # Primary splitter: recursive character-based
        self._text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", "。", ".", " ", ""],
        )

        # Markdown-aware splitter for structured documents
        self._md_headers = [
            ("#", "h1"),
            ("##", "h2"),
            ("###", "h3"),
        ]
        self._md_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self._md_headers,
        )

    def chunk_text(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
        use_markdown_splitter: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Split text into chunks with metadata.

        Args:
            text: The full document text.
            metadata: Base metadata to attach to each chunk.
            use_markdown_splitter: If True, first split on Markdown headers,
                then further split long sections.

        Returns:
            List of dicts, each with 'text' and 'metadata' keys.
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for chunking")
            return []

        base_meta = metadata or {}
        chunks: list[dict[str, Any]] = []

        if use_markdown_splitter:
            chunks = self._split_markdown(text, base_meta)
        else:
            chunks = self._split_plain(text, base_meta)

        logger.info(
            f"Chunking complete: {len(chunks)} chunks "
            f"(size={self._chunk_size}, overlap={self._chunk_overlap})"
        )
        return chunks

    def _split_plain(
        self, text: str, base_meta: dict[str, Any]
    ) -> list[dict[str, Any]]:
        docs = self._text_splitter.create_documents(
            [text], metadatas=[base_meta]
        )
        return [
            {
                "text": doc.page_content,
                "metadata": {**doc.metadata, "chunk_index": i},
            }
            for i, doc in enumerate(docs)
        ]

    def _split_markdown(
        self, text: str, base_meta: dict[str, Any]
    ) -> list[dict[str, Any]]:
        # First pass: split on headers
        md_docs = self._md_splitter.split_text(text)

        # Second pass: further split large sections
        all_chunks: list[dict[str, Any]] = []
        idx = 0
        for md_doc in md_docs:
            section_meta = {**base_meta, **md_doc.metadata}
            if len(md_doc.page_content) > self._chunk_size:
                sub_docs = self._text_splitter.create_documents(
                    [md_doc.page_content], metadatas=[section_meta]
                )
                for sub in sub_docs:
                    all_chunks.append({
                        "text": sub.page_content,
                        "metadata": {**sub.metadata, "chunk_index": idx},
                    })
                    idx += 1
            else:
                all_chunks.append({
                    "text": md_doc.page_content,
                    "metadata": {**section_meta, "chunk_index": idx},
                })
                idx += 1

        return all_chunks
