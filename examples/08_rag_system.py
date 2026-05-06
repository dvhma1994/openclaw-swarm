"""
Example: RAG (Retrieval-Augmented Generation) System
=====================================================

This example shows how to use the RAG system.
"""

from openclaw_swarm import RAGSystem, Document


def main():
    print("=" * 60)
    print("OpenClaw Swarm - RAG System Example")
    print("=" * 60)

    # 1. Create RAG System
    print("\n1. Create RAG System")
    print("-" * 40)

    rag = RAGSystem()

    print(f"Chunker size: {rag.chunker.chunk_size}")
    print(f"Chunker overlap: {rag.chunker.chunk_overlap}")
    print(f"Embedder dimension: {rag.embedder.embedding_dim}")

    # 2. Add Documents
    print("\n2. Add Documents")
    print("-" * 40)

    rag.add_document(
        content="Python is a programming language created by Guido van Rossum in 1991. "
        "It is known for its simple syntax and readability.",
        metadata={"source": "wikipedia", "topic": "python"},
    )

    rag.add_document(
        content="JavaScript is a scripting language for web browsers. "
        "It was created by Brendan Eich in 1995.",
        metadata={"source": "wikipedia", "topic": "javascript"},
    )

    rag.add_document(
        content="Machine learning is a subset of artificial intelligence. "
        "It uses statistical techniques to give computers the ability to learn.",
        metadata={"source": "textbook", "topic": "ml"},
    )

    print(f"Added {rag.get_stats()['documents']} documents")
    print(f"Created {rag.get_stats()['chunks']} chunks")
    print(f"Generated {rag.get_stats()['embeddings']} embeddings")

    # 3. Search for Relevant Documents
    print("\n3. Search for Relevant Documents")
    print("-" * 40)

    query = "programming language"
    results = rag.search(query, k=3)

    print(f"Query: {query}")
    print(f"Results: {len(results)}")

    for i, result in enumerate(results, 1):
        print(f"\n{i}. Score: {result.score:.4f}")
        print(f"   Content: {result.chunk.content[:100]}...")
        print(f"   Document ID: {result.chunk.document_id}")

    # 4. Get Context for RAG
    print("\n4. Get Context for RAG")
    print("-" * 40)

    context = rag.get_context("artificial intelligence", max_tokens=100)

    print("Context (max 100 tokens):")
    print(context[:200] + "...")

    # 5. Add Custom Metadata
    print("\n5. Add Custom Metadata")
    print("-" * 40)

    doc4 = rag.add_document(
        content="FastAPI is a modern web framework for Python. "
        "It is designed for building APIs with automatic documentation.",
        metadata={
            "source": "docs",
            "topic": "fastapi",
            "author": "Sebastián Ramírez",
            "year": 2018,
        },
    )

    print(f"Document ID: {doc4.id}")
    print(f"Metadata: {doc4.metadata}")

    # 6. Search with Minimum Score
    print("\n6. Search with Minimum Score")
    print("-" * 40)

    results = rag.search("python", k=5, min_score=0.5)

    print("Query: python (min_score: 0.5)")
    print(f"Results: {len(results)}")

    for result in results:
        print(f"  - Score: {result.score:.4f}, ID: {result.chunk.id}")

    # 7. Work with Text Chunker
    print("\n7. Work with Text Chunker")
    print("-" * 40)

    from openclaw_swarm import TextChunker

    chunker = TextChunker(chunk_size=50, chunk_overlap=10)

    long_text = (
        "This is a long piece of text that will be chunked into smaller pieces. " * 5
    )

    chunks = chunker.chunk(long_text)

    print(f"Original text length: {len(long_text)}")
    print(f"Number of chunks: {len(chunks)}")

    for i, chunk in enumerate(chunks[:3], 1):
        print(f"  Chunk {i}: {len(chunk)} chars")

    # 8. Work with Embedder
    print("\n8. Work with Embedder")
    print("-" * 40)

    from openclaw_swarm import SimpleEmbedder

    embedder = SimpleEmbedder(embedding_dim=128)

    emb1 = embedder.embed("Hello World")
    emb2 = embedder.embed("Hello World")
    emb3 = embedder.embed("Different text")

    print(f"Embedding dimension: {len(emb1)}")
    print(f"Same text embeddings equal: {emb1 == emb2}")
    print(f"Different text embeddings different: {emb1 != emb3}")

    # 9. Work with Vector Store
    print("\n9. Work with Vector Store")
    print("-" * 40)

    from openclaw_swarm import VectorStore

    store = VectorStore()

    doc = Document(
        id="test",
        content="Vector stores enable fast similarity search",
        metadata={"type": "test"},
    )

    store.add_document(doc)

    results = store.search("similarity")

    print(f"Documents in store: {store.get_stats()['documents']}")
    print(f"Chunks in store: {store.get_stats()['chunks']}")
    print(f"Search results: {len(results)}")

    # 10. Delete Document
    print("\n10. Delete Document")
    print("-" * 40)

    stats_before = rag.get_stats()
    rag.delete_document(doc4.id)
    stats_after = rag.get_stats()

    print(f"Documents before: {stats_before['documents']}")
    print(f"Documents after: {stats_after['documents']}")

    # 11. Clear System
    print("\n11. Clear System")
    print("-" * 40)

    rag.clear()

    stats = rag.get_stats()
    print(f"Documents after clear: {stats['documents']}")
    print(f"Chunks after clear: {stats['chunks']}")

    # 12. Persistence Example
    print("\n12. Persistence Example")
    print("-" * 40)

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create and save
        rag1 = RAGSystem(storage_path=tmpdir)
        rag1.add_document("This will be saved to disk")

        # Load in new instance
        rag2 = RAGSystem(storage_path=tmpdir)

        stats = rag2.get_stats()
        print(f"Loaded documents: {stats['documents']}")

    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
