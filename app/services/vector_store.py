"""ChromaDB vector store service.

Manages embedding generation and persistent storage of document chunks
for semantic search and retrieval.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from loguru import logger

from app.core.config import get_settings


class VectorStoreService:
    """Wraps ChromaDB for document chunk storage and retrieval."""

    def __init__(self) -> None:
        self._client = None
        self._embedding_fn = None
        self._default_collection_name = "idp_documents"

    async def initialize(self) -> None:
        """Initialize ChromaDB client and embedding function."""
        settings = get_settings()

        def _setup():
            import chromadb
            from chromadb.utils import embedding_functions

            client = chromadb.PersistentClient(path=settings.chroma_persist_dir)

            ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=settings.embedding_model
            )

            return client, ef

        try:
            self._client, self._embedding_fn = await asyncio.to_thread(_setup)
            logger.info("ChromaDB initialized with persistent storage")
        except ImportError:
            logger.warning(
                "ChromaDB or sentence-transformers not installed. "
                "Vector store will be unavailable."
            )

    async def is_available(self) -> bool:
        return self._client is not None

    async def store_chunks(
        self,
        chunks: list[dict[str, Any]],
        collection_name: str | None = None,
        source_file: str = "unknown",
    ) -> list[str]:
        """
        Store document chunks in ChromaDB.

        Args:
            chunks: List of dicts with 'text' and 'metadata' keys.
            collection_name: ChromaDB collection name.
            source_file: Original filename for metadata.

        Returns:
            List of generated vector IDs.
        """
        if self._client is None:
            logger.warning("ChromaDB not available — skipping vector storage")
            return []

        col_name = collection_name or self._default_collection_name

        def _store():
            collection = self._client.get_or_create_collection(
                name=col_name,
                embedding_function=self._embedding_fn,
            )

            ids: list[str] = []
            documents: list[str] = []
            metadatas: list[dict] = []

            for chunk in chunks:
                chunk_id = str(uuid.uuid4())
                ids.append(chunk_id)
                documents.append(chunk["text"])
                meta = {**chunk.get("metadata", {}), "source": source_file}
                # ChromaDB requires metadata values to be str/int/float/bool
                clean_meta = {
                    k: str(v) if not isinstance(v, (str, int, float, bool)) else v
                    for k, v in meta.items()
                }
                metadatas.append(clean_meta)

            # Batch insert (ChromaDB handles embedding automatically)
            batch_size = 100
            for i in range(0, len(ids), batch_size):
                collection.add(
                    ids=ids[i : i + batch_size],
                    documents=documents[i : i + batch_size],
                    metadatas=metadatas[i : i + batch_size],
                )

            return ids

        try:
            vector_ids = await asyncio.to_thread(_store)
            logger.info(f"Stored {len(vector_ids)} chunks in collection '{col_name}'")
            return vector_ids
        except Exception as exc:
            logger.error(f"Vector storage failed: {exc}")
            return []

    async def search(
        self,
        query: str,
        top_k: int = 5,
        collection_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Semantic search across stored chunks.

        Returns list of dicts with 'text', 'score', and 'metadata'.
        """
        if self._client is None:
            return []

        col_name = collection_name or self._default_collection_name

        def _query():
            collection = self._client.get_or_create_collection(
                name=col_name,
                embedding_function=self._embedding_fn,
            )
            results = collection.query(query_texts=[query], n_results=top_k)

            hits: list[dict[str, Any]] = []
            if results and results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    hits.append({
                        "text": doc,
                        "score": (
                            1.0 - results["distances"][0][i]
                            if results.get("distances")
                            else 0.0
                        ),
                        "metadata": (
                            results["metadatas"][0][i]
                            if results.get("metadatas")
                            else {}
                        ),
                    })
            return hits

        try:
            return await asyncio.to_thread(_query)
        except Exception as exc:
            logger.error(f"Vector search failed: {exc}")
            return []
