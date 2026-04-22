"""
Tests for RAG System
"""

import os
import tempfile

from openclaw_swarm.rag import (
    Chunk,
    Document,
    RAGSystem,
    SearchResult,
    SimpleEmbedder,
    TextChunker,
    VectorStore,
)


class TestDocument:
    """Test Document dataclass"""

    def test_document_creation(self):
        """Test creating a document"""
        doc = Document(id="test", content="Hello World")

        assert doc.id == "test"
        assert doc.content == "Hello World"
        assert doc.metadata == {}
        assert doc.embedding is None
        assert doc.created_at is not None

    def test_document_with_metadata(self):
        """Test document with metadata"""
        doc = Document(
            id="test",
            content="Hello",
            metadata={"author": "test", "date": "2024-01-01"},
        )

        assert doc.metadata["author"] == "test"

    def test_document_auto_id(self):
        """Test document auto-generated ID"""
        doc = Document(id="", content="Hello")

        # Empty ID gets replaced with hash
        assert doc.id != ""


class TestChunk:
    """Test Chunk dataclass"""

    def test_chunk_creation(self):
        """Test creating a chunk"""
        chunk = Chunk(
            id="test_chunk",
            document_id="doc1",
            content="Hello",
            start_char=0,
            end_char=5,
        )

        assert chunk.id == "test_chunk"
        assert chunk.document_id == "doc1"
        assert chunk.content == "Hello"
        assert chunk.start_char == 0
        assert chunk.end_char == 5


class TestTextChunker:
    """Test TextChunker"""

    def test_chunker_initialization(self):
        """Test chunker initialization"""
        chunker = TextChunker(chunk_size=1000, chunk_overlap=200)

        assert chunker.chunk_size == 1000
        assert chunker.chunk_overlap == 200

    def test_chunk_small_text(self):
        """Test chunking small text"""
        chunker = TextChunker(chunk_size=100)
        text = "Hello World"

        chunks = chunker.chunk(text)

        assert len(chunks) == 1
        assert chunks[0] == "Hello World"

    def test_chunk_large_text(self):
        """Test chunking large text"""
        chunker = TextChunker(chunk_size=50, chunk_overlap=10)
        text = "A" * 200

        chunks = chunker.chunk(text)

        assert len(chunks) > 1

    def test_chunk_document(self):
        """Test chunking a document"""
        chunker = TextChunker(chunk_size=50)
        doc = Document(id="doc1", content="A" * 200)

        chunks = chunker.chunk_document(doc)

        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk.document_id == "doc1"


class TestSimpleEmbedder:
    """Test SimpleEmbedder"""

    def test_embedder_initialization(self):
        """Test embedder initialization"""
        embedder = SimpleEmbedder(embedding_dim=384)

        assert embedder.embedding_dim == 384

    def test_embed_returns_list(self):
        """Test embed returns list"""
        embedder = SimpleEmbedder()

        embedding = embedder.embed("Hello World")

        assert isinstance(embedding, list)
        assert len(embedding) == 384

    def test_embed_different_texts(self):
        """Test embedding different texts"""
        embedder = SimpleEmbedder()

        emb1 = embedder.embed("Hello")
        emb2 = embedder.embed("World")

        assert emb1 != emb2

    def test_embed_batch(self):
        """Test embedding batch"""
        embedder = SimpleEmbedder()

        embeddings = embedder.embed_batch(["Hello", "World"])

        assert len(embeddings) == 2
        assert len(embeddings[0]) == 384


class TestVectorStore:
    """Test VectorStore"""

    def test_store_initialization(self):
        """Test store initialization"""
        store = VectorStore()

        assert len(store.chunks) == 0
        assert len(store.documents) == 0

    def test_add_document(self):
        """Test adding a document"""
        store = VectorStore()
        doc = Document(id="doc1", content="Hello World")

        store.add_document(doc)

        assert "doc1" in store.documents
        assert len(store.chunks) >= 1

    def test_add_chunk(self):
        """Test adding a chunk"""
        store = VectorStore()
        chunk = Chunk(
            id="chunk1", document_id="doc1", content="Hello", start_char=0, end_char=5
        )

        store.add_chunk(chunk)

        assert "chunk1" in store.chunks

    def test_search(self):
        """Test searching"""
        store = VectorStore()
        doc = Document(id="doc1", content="Python is a programming language")

        store.add_document(doc)

        results = store.search("programming", k=1)

        assert len(results) >= 1
        assert isinstance(results[0], SearchResult)

    def test_search_with_min_score(self):
        """Test searching with minimum score"""
        store = VectorStore()
        doc = Document(id="doc1", content="Python is a programming language")

        store.add_document(doc)

        results = store.search("xyz", k=5, min_score=0.99)

        # Should have no results with high min_score
        assert len(results) == 0

    def test_delete_document(self):
        """Test deleting a document"""
        store = VectorStore()
        doc = Document(id="doc1", content="Hello World")

        store.add_document(doc)
        store.delete_document("doc1")

        assert "doc1" not in store.documents

    def test_clear(self):
        """Test clearing store"""
        store = VectorStore()
        doc = Document(id="doc1", content="Hello")

        store.add_document(doc)
        store.clear()

        assert len(store.documents) == 0
        assert len(store.chunks) == 0

    def test_get_stats(self):
        """Test getting statistics"""
        store = VectorStore()
        doc = Document(id="doc1", content="Hello World")

        store.add_document(doc)

        stats = store.get_stats()

        assert stats["documents"] == 1
        assert stats["chunks"] >= 1


class TestRAGSystem:
    """Test RAGSystem"""

    def test_rag_initialization(self):
        """Test RAG system initialization"""
        rag = RAGSystem()

        assert rag.embedder is not None
        assert rag.chunker is not None
        assert rag.vector_store is not None

    def test_add_document(self):
        """Test adding a document"""
        rag = RAGSystem()

        doc = rag.add_document("Python is a programming language")

        assert doc.id is not None

        stats = rag.get_stats()
        assert stats["documents"] == 1

    def test_add_document_with_metadata(self):
        """Test adding document with metadata"""
        rag = RAGSystem()

        doc = rag.add_document(
            content="Hello World", metadata={"author": "test", "category": "test"}
        )

        assert doc.metadata["author"] == "test"

    def test_add_file(self):
        """Test adding a file"""
        rag = RAGSystem()

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Test file content")
            filepath = f.name

        try:
            doc = rag.add_file(filepath)

            assert doc.metadata["filename"] is not None
            assert "Test file content" in doc.content
        finally:
            os.unlink(filepath)

    def test_search(self):
        """Test searching"""
        rag = RAGSystem()

        rag.add_document("Python is a programming language")
        rag.add_document("JavaScript is also a programming language")
        rag.add_document("Apples are fruits")

        results = rag.search("programming", k=2)

        assert len(results) >= 1

    def test_get_context(self):
        """Test getting context"""
        rag = RAGSystem()

        rag.add_document(
            "Python is a programming language created by Guido van Rossum."
        )
        rag.add_document("JavaScript is a scripting language for web browsers.")

        context = rag.get_context("programming", max_tokens=100)

        assert len(context) > 0

    def test_delete_document(self):
        """Test deleting a document"""
        rag = RAGSystem()

        doc = rag.add_document("Test content")
        rag.delete_document(doc.id)

        stats = rag.get_stats()
        assert stats["documents"] == 0

    def test_clear(self):
        """Test clearing system"""
        rag = RAGSystem()

        rag.add_document("Test 1")
        rag.add_document("Test 2")
        rag.clear()

        stats = rag.get_stats()
        assert stats["documents"] == 0

    def test_persistence(self):
        """Test persistence to disk"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create and save
            rag1 = RAGSystem(storage_path=tmpdir)
            rag1.add_document("Test content for persistence")

            # Create new instance and load
            rag2 = RAGSystem(storage_path=tmpdir)

            stats = rag2.get_stats()
            assert stats["documents"] >= 1
