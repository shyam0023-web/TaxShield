#!/usr/bin/env python3
"""
Demo: Load circulars into Supabase pgvector WITHOUT OpenAI API key
Uses simulated embeddings for testing the vector search

This is a proof-of-concept. For production, use real OpenAI embeddings.
"""
import asyncio
import sys
import os
import random
import numpy as np
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.supabase_client import supabase_client
from app.retrieval.pgvector_search import document_vector_store
from app.retrieval.ingestion import load_circulars
from app.rag.vector_store import chunk_text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_mock_embedding(text: str) -> list:
    """
    Generate a mock embedding without OpenAI
    In production, use: call_embedding_api(text)
    """
    # For demo: use a simple hash-based "embedding"
    # Seeds the random with text hash so same text = same embedding
    random.seed(hash(text) % (2**32))
    embedding = [random.uniform(-1, 1) for _ in range(1536)]
    return embedding


async def migrate_documents_demo():
    """Migrate circulars using mock embeddings"""
    
    print("\n" + "="*60)
    print("🚀 Demo: Load Circulars into Supabase pgvector")
    print("="*60)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Connect to Supabase
    print("📡 Connecting to Supabase...")
    connected = await supabase_client.connect()
    if not connected:
        print("❌ Failed to connect to Supabase")
        return False
    
    print("✅ Connected to Supabase PostgreSQL\n")
    
    # Load documents
    print("📚 Loading circulars...")
    documents = load_circulars("data/circulars")
    if not documents:
        print("⚠️  No documents found")
        return False
    
    print(f"✅ Found {len(documents)} documents\n")
    
    total_docs = 0
    total_chunks = 0
    failed = []
    
    # Process each document
    for doc_num, doc in enumerate(documents, 1):
        print(f"[{doc_num}/{len(documents)}] 📄 {doc.doc_id[:40]}")
        
        try:
            # Create document
            doc_id = await document_vector_store.add_document(
                doc_id=doc.doc_id,
                title=doc.title[:256],
                content=doc.text,
                source_url=doc.metadata.get("source_url"),
                metadata=doc.metadata
            )
            
            if not doc_id:
                print(f"        ❌ Failed to create document")
                failed.append(doc.doc_id)
                continue
            
            total_docs += 1
            
            # Chunk the document
            chunks = chunk_text(doc.text, chunk_size=800, overlap=100)
            print(f"        📦 {len(chunks)} chunks")
            
            # Store chunks with MOCK embeddings
            successful = 0
            for chunk_idx, chunk_text_content in enumerate(chunks):
                try:
                    # Generate mock embedding (no OpenAI API call)
                    embedding = generate_mock_embedding(chunk_text_content)
                    
                    # Store chunk
                    success = await document_vector_store.add_chunk_with_embedding(
                        document_id=doc_id,
                        chunk_index=chunk_idx,
                        chunk_text=chunk_text_content,
                        embedding=embedding,
                        embedding_model="mock-demo"
                    )
                    
                    if success:
                        successful += 1
                        total_chunks += 1
                        
                        if (chunk_idx + 1) % 10 == 0:
                            print(f"           ✓ {chunk_idx + 1}/{len(chunks)}")
                    
                except Exception as e:
                    if chunk_idx < 3:
                        print(f"           ✗ {chunk_idx}: {str(e)[:40]}")
            
            print(f"        ✅ {successful}/{len(chunks)} chunks stored\n")
            
        except Exception as e:
            print(f"        ❌ Error: {e}\n")
            failed.append(doc.doc_id)
    
    # Summary
    print("="*60)
    print("📊 Demo Summary")
    print("="*60)
    print(f"✅ Documents: {total_docs}/{len(documents)}")
    print(f"✅ Chunks: {total_chunks}")
    print(f"✅ Embedding model: mock-demo (for testing)")
    
    if failed:
        print(f"❌ Failed: {len(failed)}")
        for doc_id in failed[:3]:
            print(f"   - {doc_id}")
    
    # Test search
    print(f"\n🔍 Testing pgvector search...")
    try:
        test_embedding = generate_mock_embedding("GST limitation period assessment")
        results = await supabase_client.search_chunks_by_embedding(
            embedding=test_embedding,
            limit=3,
            similarity_threshold=0.0  # Very low threshold for demo
        )
        
        print(f"✅ Search returned {len(results)} results")
        if results:
            print(f"   Top result: {results[0].get('chunk_text', '')[:60]}...")
    except Exception as e:
        print(f"⚠️  Search test: {e}")
    
    print(f"\n✨ Demo completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    await supabase_client.disconnect()
    return len(failed) == 0


if __name__ == "__main__":
    print("\n⚠️  NOTE: This is a DEMO using mock embeddings for testing.")
    print("For production with real OpenAI embeddings:")
    print("  1. Add OPENAI_API_KEY to .env")
    print("  2. Run: python migrate_rag_to_supabase.py\n")
    
    success = asyncio.run(migrate_documents_demo())
    sys.exit(0 if success else 1)
