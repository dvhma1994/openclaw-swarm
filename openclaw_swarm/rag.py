"""
OpenClaw Swarm - RAG (Retrieval-Augmented Generation) System
Vector-based document retrieval and generation
"""

import os
import json
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class Document:
    """A document in the RAG system"""

    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if not self.id:
            self.id = hashlib.md5(self.content.encode()).hexdigest()


@dataclass
class Chunk:
    """A chunk of a document"""

    id: str
    document_id: str
    content: str
    start_char: int
    end_char: int
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """Result from a RAG search"""

    chunk: Chunk
    score: float
    document: Optional[Document] = None


class TextChunker:
    """Split documents into chunks"""

    def __init__(
        self, chunk_size: int = 1000, chunk_overlap: int = 200, separator: str = "\n\n"
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator

    def chunk(self, text: str) -> List[str]:
        """Split text into chunks"""
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size

            # Try to find a natural break point
            if end < len(text):
                # Look for separator near the end
                break_point = text.rfind(self.separator, start, end)
                if break_point > start:
                    end = break_point + len(self.separator)

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start with overlap
            start = end - self.chunk_overlap
            if start < 0:
                start = 0

            # Avoid infinite loop
            if start >= end:
                start = end

        return chunks

    def chunk_document(self, document: Document) -> List[Chunk]:
        """Chunk a document"""
        chunks = self.chunk(document.content)

        result = []
        current_pos = 0

        for i, chunk_content in enumerate(chunks):
            start_char = document.content.find(chunk_content, current_pos)
            end_char = start_char + len(chunk_content)

            chunk = Chunk(
                id=f"{document.id}_chunk_{i}",
                document_id=document.id,
                content=chunk_content,
                start_char=start_char,
                end_char=end_char,
                metadata={
                    **document.metadata,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                },
            )

            result.append(chunk)
            current_pos = end_char

        return result


class SimpleEmbedder:
    """Simple text embedder using hash-based approach (no ML required)"""

    def __init__(self, embedding_dim: int = 384):
        self.embedding_dim = embedding_dim

    def embed(self, text: str) -> List[float]:
        """Create embedding for text (simple hash-based)"""
        # This is a simple deterministic embedding for demonstration
        # In production, use sentence-transformers or similar
        text_hash = hashlib.sha256(text.encode()).hexdigest()

        # Convert hash to float vector
        embedding = []
        for i in range(0, min(len(text_hash), self.embedding_dim * 2), 2):
            if i + 1 < len(text_hash):
                val = int(text_hash[i : i + 2], 16) / 255.0
                embedding.append(val)

        # Pad or truncate to desired dimension
        while len(embedding) < self.embedding_dim:
            embedding.append(0.0)

        return embedding[: self.embedding_dim]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts"""
        return [self.embed(text) for text in texts]


class VectorStore:
    """Simple in-memory vector store"""

    def __init__(self, embedder: Optional[SimpleEmbedder] = None):
        self.embedder = embedder or SimpleEmbedder()
        self.chunks: Dict[str, Chunk] = {}
        self.documents: Dict[str, Document] = {}
        self.embeddings: Dict[str, List[float]] = {}

    def add_document(self, document: Document, chunker: Optional[TextChunker] = None):
        """Add a document to the store"""
        # Store document
        self.documents[document.id] = document

        # Chunk document
        chunker = chunker or TextChunker()
        chunks = chunker.chunk_document(document)

        # Add chunks with embeddings
        for chunk in chunks:
            chunk.embedding = self.embedder.embed(chunk.content)
            self.chunks[chunk.id] = chunk
            self.embeddings[chunk.id] = chunk.embedding

    def add_chunk(self, chunk: Chunk):
        """Add a single chunk"""
        if not chunk.embedding:
            chunk.embedding = self.embedder.embed(chunk.content)

        self.chunks[chunk.id] = chunk
        self.embeddings[chunk.id] = chunk.embedding

    def search(
        self, query: str, k: int = 5, min_score: float = 0.0
    ) -> List[SearchResult]:
        """Search for similar chunks"""
        query_embedding = self.embedder.embed(query)

        results = []
        for chunk_id, chunk_embedding in self.embeddings.items():
            score = self._cosine_similarity(query_embedding, chunk_embedding)

            if score >= min_score:
                chunk = self.chunks[chunk_id]
                document = self.documents.get(chunk.document_id)

                results.append(
                    SearchResult(chunk=chunk, score=score, document=document)
                )

        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)

        return results[:k]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if len(a) != len(b):
            return 0.0

        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    def delete_document(self, document_id: str):
        """Delete a document and its chunks"""
        # Delete document
        if document_id in self.documents:
            del self.documents[document_id]

        # Delete chunks
        chunk_ids_to_delete = [
            chunk_id
            for chunk_id, chunk in self.chunks.items()
            if chunk.document_id == document_id
        ]

        for chunk_id in chunk_ids_to_delete:
            del self.chunks[chunk_id]
            if chunk_id in self.embeddings:
                del self.embeddings[chunk_id]

    def clear(self):
        """Clear all documents and chunks"""
        self.documents.clear()
        self.chunks.clear()
        self.embeddings.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics"""
        return {
            "documents": len(self.documents),
            "chunks": len(self.chunks),
            "embeddings": len(self.embeddings),
        }


class RAGSystem:
    """Complete RAG system"""

    def __init__(
        self,
        storage_path: Optional[str] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        embedding_dim: int = 384,
    ):
        self.storage_path = Path(storage_path) if storage_path else None
        self.embedder = SimpleEmbedder(embedding_dim)
        self.chunker = TextChunker(chunk_size, chunk_overlap)
        self.vector_store = VectorStore(self.embedder)

        if self.storage_path:
            self._load_from_disk()

    def add_document(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None,
    ) -> Document:
        """Add a document to the RAG system"""
        document = Document(id=doc_id or "", content=content, metadata=metadata or {})

        self.vector_store.add_document(document, self.chunker)

        if self.storage_path:
            self._save_to_disk()

        return document

    def add_file(
        self, file_path: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Document:
        """Add a file to the RAG system"""
        path = Path(file_path)

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        file_metadata = {
            "filename": path.name,
            "path": str(path),
            "extension": path.suffix,
            **(metadata or {}),
        }

        return self.add_document(content, file_metadata)

    def search(
        self, query: str, k: int = 5, min_score: float = 0.0
    ) -> List[SearchResult]:
        """Search for relevant chunks"""
        return self.vector_store.search(query, k, min_score)

    def get_context(
        self, query: str, max_tokens: int = 4000, min_score: float = 0.3
    ) -> str:
        """Get context for a query (for RAG generation)"""
        results = self.search(query, k=20, min_score=min_score)

        context_parts = []
        current_tokens = 0

        for result in results:
            # Estimate tokens (rough: 4 chars per token)
            chunk_tokens = len(result.chunk.content) // 4

            if current_tokens + chunk_tokens > max_tokens:
                break

            context_parts.append(result.chunk.content)
            current_tokens += chunk_tokens

        return "\n\n---\n\n".join(context_parts)

    def delete_document(self, document_id: str):
        """Delete a document"""
        self.vector_store.delete_document(document_id)

        if self.storage_path:
            self._save_to_disk()

    def clear(self):
        """Clear all documents"""
        self.vector_store.clear()

        if self.storage_path:
            self._save_to_disk()

    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        return self.vector_store.get_stats()

    def _save_to_disk(self):
        """Save to disk"""
        if not self.storage_path:
            return

        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Save documents
        docs_file = self.storage_path / "documents.json"
        docs_data = {
            doc_id: {
                "id": doc.id,
                "content": doc.content,
                "metadata": doc.metadata,
                "created_at": doc.created_at.isoformat(),
            }
            for doc_id, doc in self.vector_store.documents.items()
        }

        with open(docs_file, "w", encoding="utf-8") as f:
            json.dump(docs_data, f, indent=2)

    def _load_from_disk(self):
        """Load from disk"""
        if not self.storage_path:
            return

        docs_file = self.storage_path / "documents.json"

        if not docs_file.exists():
            return

        with open(docs_file, "r", encoding="utf-8") as f:
            docs_data = json.load(f)

        for doc_id, doc_data in docs_data.items():
            document = Document(
                id=doc_data["id"],
                content=doc_data["content"],
                metadata=doc_data["metadata"],
                created_at=datetime.fromisoformat(doc_data["created_at"]),
            )

            self.vector_store.add_document(document, self.chunker)
