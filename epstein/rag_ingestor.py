"""
RAG Document Ingestion System
Feeds documents to Qdrant vector database for semantic search and analysis.
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """Represents a chunk of a document for RAG."""

    chunk_id: str
    doc_id: str
    text: str
    start_offset: int
    end_offset: int
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Document:
    """Represents a document in the RAG system."""

    doc_id: str
    source_url: str
    title: str
    doc_type: str  # flight_log, email, meeting, financial, phone_record
    content: str
    sha256: str
    file_size: int
    chunks: List[DocumentChunk] = field(default_factory=list)
    entities: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class RAGIngestor:
    """
    Handles ingestion of documents into the RAG system.
    Supports Qdrant, Chroma, or simple file-based storage.
    """

    def __init__(
        self,
        vector_store: str = "qdrant",  # qdrant, chroma, memory
        qdrant_url: str = "http://localhost:6333",
        collection_name: str = "epstein_documents",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        self.vector_store = vector_store
        self.qdrant_url = qdrant_url
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.embedder = None
        self.qdrant_client = None
        self.documents: Dict[str, Document] = {}

    def _get_embedder(self):
        """Lazy load embedding model."""
        if self.embedder is None:
            try:
                from sentence_transformers import SentenceTransformer

                self.embedder = SentenceTransformer(self.embedding_model)
                logger.info(f"Loaded embedding model: {self.embedding_model}")
            except ImportError:
                logger.warning("sentence-transformers not available, using mock embeddings")
                self.embedder = self._mock_embedder
        return self.embedder

    def _mock_embedder(self, texts: List[str]) -> np.ndarray:
        """Mock embedder for testing."""
        return np.random.rand(len(texts), 384).astype(float)

    def _get_qdrant_client(self):
        """Lazy load Qdrant client."""
        if self.qdrant_client is None:
            try:
                from qdrant_client import QdrantClient

                self.qdrant_client = QdrantClient(url=self.qdrant_url)
                logger.info(f"Connected to Qdrant at {self.qdrant_url}")
            except ImportError:
                logger.warning("Qdrant client not available, using in-memory storage")
                self.qdrant_client = None
        return self.qdrant_client

    def generate_chunks(
        self,
        text: str,
        doc_id: str,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
    ) -> List[DocumentChunk]:
        """Split document text into chunks."""
        chunks = []
        start = 0
        chunk_idx = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end]

            chunk_id = f"{doc_id}_chunk_{chunk_idx}"
            chunk = DocumentChunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                text=chunk_text,
                start_offset=start,
                end_offset=end,
            )
            chunks.append(chunk)

            start = end - chunk_overlap
            chunk_idx += 1

        logger.info(f"Generated {len(chunks)} chunks for doc {doc_id}")
        return chunks

    def embed_chunks(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """Generate embeddings for chunks."""
        embedder = self._get_embedder()
        texts = [chunk.text for chunk in chunks]

        # Get embeddings
        if hasattr(embedder, "__call__"):
            embeddings = embedder(texts)
        else:
            embeddings = embedder.encode(texts)

        # Attach embeddings to chunks
        for i, chunk in enumerate(chunks):
            chunk.embedding = (
                embeddings[i].tolist() if hasattr(embeddings[i], "tolist") else list(embeddings[i])
            )

        return chunks

    def ingest_document(
        self,
        source_url: str,
        title: str,
        doc_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Document:
        """Ingest a document into the RAG system."""
        # Generate document ID from content hash
        doc_id = hashlib.sha256(content.encode()).hexdigest()[:16]

        # Check if already ingested
        if doc_id in self.documents:
            logger.info(f"Document {doc_id} already ingested, skipping")
            return self.documents[doc_id]

        # Generate chunks
        chunks = self.generate_chunks(content, doc_id)

        # Generate embeddings
        chunks = self.embed_chunks(chunks)

        # Create document
        sha256 = hashlib.sha256(content.encode()).hexdigest()
        document = Document(
            doc_id=doc_id,
            source_url=source_url,
            title=title,
            doc_type=doc_type,
            content=content,
            sha256=sha256,
            file_size=len(content.encode()),
            chunks=chunks,
            metadata=metadata or {},
        )

        # Store in Qdrant or memory
        self._store_in_vector_db(document)

        # Keep in memory for quick access
        self.documents[doc_id] = document

        logger.info(f"Ingested document {doc_id}: {title} ({len(chunks)} chunks)")
        return document

    def _store_in_vector_db(self, document: Document):
        """Store document chunks in vector database."""
        client = self._get_qdrant_client()

        if client is None:
            # Use in-memory storage
            return

        try:
            # Ensure collection exists
            collections = client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.collection_name not in collection_names:
                from qdrant_client.models import Distance, VectorParams

                client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=384,
                        distance=Distance.COSINE,
                    ),
                )

            # Prepare points for insertion
            from qdrant_client.models import PointStruct

            points = []
            for chunk in document.chunks:
                if chunk.embedding:
                    points.append(
                        PointStruct(
                            id=chunk.chunk_id,
                            vector=chunk.embedding,
                            payload={
                                "doc_id": document.doc_id,
                                "chunk_id": chunk.chunk_id,
                                "text": chunk.text,
                                "title": document.title,
                                "doc_type": document.doc_type,
                                "source_url": document.source_url,
                                "chunk_idx": chunk.chunk_id.split("_")[-1],
                            },
                        )
                    )

            if points:
                client.upsert(
                    collection_name=self.collection_name,
                    points=points,
                )

        except Exception as e:
            logger.error(f"Error storing in Qdrant: {e}")

    def search(
        self,
        query: str,
        limit: int = 10,
        doc_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Semantic search across documents."""
        embedder = self._get_embedder()
        client = self._get_qdrant_client()

        # Generate query embedding
        if hasattr(embedder, "__call__"):
            query_embedding = embedder([query])[0]
        else:
            query_embedding = embedder.encode([query])[0]

        if hasattr(query_embedding, "tolist"):
            query_embedding = query_embedding.tolist()

        if client is None:
            # Simple in-memory search
            return self._memory_search(query, limit, doc_type)

        try:
            # Search Qdrant
            from qdrant_client.models import Filter, FieldCondition, Match

            search_params = {"limit": limit}

            # Add filter if doc_type specified
            if doc_type:
                search_params["query_filter"] = Filter(
                    must=[FieldCondition(key="doc_type", match=Match(value=doc_type))]
                )

            results = client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                **search_params,
            )

            return [
                {
                    "chunk_id": r.id,
                    "text": r.payload.get("text"),
                    "title": r.payload.get("title"),
                    "doc_type": r.payload.get("doc_type"),
                    "score": r.score,
                    "doc_id": r.payload.get("doc_id"),
                }
                for r in results
            ]

        except Exception as e:
            logger.error(f"Error searching Qdrant: {e}")
            return self._memory_search(query, limit, doc_type)

    def _memory_search(
        self,
        query: str,
        limit: int,
        doc_type: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Simple in-memory search."""
        results = []
        query_lower = query.lower()

        for doc in self.documents.values():
            if doc_type and doc.doc_type != doc_type:
                continue

            for chunk in doc.chunks:
                if query_lower in chunk.text.lower():
                    results.append(
                        {
                            "chunk_id": chunk.chunk_id,
                            "text": chunk.text,
                            "title": doc.title,
                            "doc_type": doc.doc_type,
                            "score": 1.0,
                            "doc_id": doc.doc_id,
                        }
                    )

                    if len(results) >= limit:
                        break

            if len(results) >= limit:
                break

        return results

    def get_document(self, doc_id: str) -> Optional[Document]:
        """Get a document by ID."""
        return self.documents.get(doc_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get RAG system statistics."""
        total_docs = len(self.documents)
        total_chunks = sum(len(d.chunks) for d in self.documents.values())

        doc_types = {}
        for doc in self.documents.values():
            doc_types[doc.doc_type] = doc_types.get(doc.doc_type, 0) + 1

        return {
            "total_documents": total_docs,
            "total_chunks": total_chunks,
            "doc_types": doc_types,
            "vector_store": self.vector_store,
        }


# Convenience function for quick ingestion
def quick_ingest(
    content: str, title: str, doc_type: str, source_url: str = "", **kwargs
) -> Document:
    """Quick way to ingest a document."""
    ingestor = RAGIngestor(**kwargs)
    return ingestor.ingest_document(
        source_url=source_url,
        title=title,
        doc_type=doc_type,
        content=content,
    )
