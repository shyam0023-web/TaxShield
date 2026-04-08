#!/usr/bin/env python3
"""
Migrate existing RAG documents from FAISS/local to Supabase pgvector

Usage:
    python migrate_rag_to_supabase.py

This script:
1. Connects to Supabase
2. Loads all circulars from data/circulars/
3. Creates document records
4. Chunks documents
5. Generates embeddings
6. Stores chunks with embeddings in pgvector
"""
import asyncio
import sys
import os
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.supabase_client import supabase_client
from app.retrieval.pgvector_search import document_vector_store
from app.retrieval.ingestion import load_circulars
from app.rag.rag_service import call_embedding_api
from app.rag.vector_store import chunk_text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate_documents():
    """Migrate all circulars to Supabase pgvector"""
    
    print("\n" + "="*60)
    print("🚀 Supabase RAG Migration Tool")
    print("="*60)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Connect to Supabase
    print("📡 Connecting to Supabase...")
    connected = await supabase_client.connect()
    if not connected:
        print("❌ Failed to connect to Supabase")
        print("   Check your .env file has SUPABASE_* variables set")
        return False
    
    print("✅ Connected to Supabase PostgreSQL\n")
    
    # Load existing documents
    print("📚 Loading documents from data/circulars/...")
    documents = load_circulars("data/circulars")
    if not documents:
        print("⚠️  No documents found in data/circulars/")
        print("    Checked paths:")
        print("    - data/circulars/")
        print("    - backend/data/circulars/")
        return False
    
    print(f"✅ Found {len(documents)} documents\n")
    
    # Migration stats
    total_docs = 0
    total_chunks = 0
    total_embeddings = 0
    failed_docs = []
    
    # Process each document
    for doc_num, doc in enumerate(documents, 1):
        print(f"[{doc_num}/{len(documents)}] 📄 {doc.doc_id[:40]}")
        
        try:
            # Create document in Supabase
            doc_id = await document_vector_store.add_document(
                doc_id=doc.doc_id,
                title=doc.title[:256],
                content=doc.text,
                source_url=doc.metadata.get("source_url"),
                metadata=doc.metadata
            )
            
            if not doc_id:
                print(f"        ❌ Failed to create document record")
                failed_docs.append(doc.doc_id)
                continue
            
            total_docs += 1
            
            # Chunk the document
            chunks = chunk_text(doc.text, chunk_size=800, overlap=100)
            print(f"        📦 Chunked into {len(chunks)} pieces")
            
            # Embed and store each chunk
            successful_chunks = 0
            failed_chunks = 0
            
            for chunk_idx, chunk_text_content in enumerate(chunks):
                try:
                    # Generate embedding
                    embedding = call_embedding_api(chunk_text_content)
                    
                    # Store chunk with embedding
                    success = await document_vector_store.add_chunk_with_embedding(
                        document_id=doc_id,
                        chunk_index=chunk_idx,
                        chunk_text=chunk_text_content,
                        embedding=embedding,
                        embedding_model="text-embedding-3-small"
                    )
                    
                    if success:
                        successful_chunks += 1
                        total_chunks += 1
                        total_embeddings += 1
                        
                        # Progress indicator
                        if (chunk_idx + 1) % 10 == 0:
                            print(f"           • {chunk_idx + 1}/{len(chunks)} chunks")
                    else:
                        failed_chunks += 1
                        
                except Exception as e:
                    failed_chunks += 1
                    if chunk_idx < 3:  # Show first 3 errors
                        print(f"           ✗ Chunk {chunk_idx}: {str(e)[:50]}")
            
            print(f"        ✅ {successful_chunks}/{len(chunks)} chunks stored")
            if failed_chunks > 0:
                print(f"        ⚠️  {failed_chunks} chunks failed")
            
            print()
            
        except Exception as e:
            print(f"        ❌ Error: {e}\n")
            failed_docs.append(doc.doc_id)
            continue
    
    # Final report
    print("="*60)
    print("📊 Migration Summary")
    print("="*60)
    print(f"✅ Documents processed:     {total_docs}/{len(documents)}")
    print(f"✅ Chunks created:           {total_chunks}")
    print(f"✅ Embeddings generated:     {total_embeddings}")
    
    if failed_docs:
        print(f"❌ Failed documents:        {len(failed_docs)}")
        for doc_id in failed_docs[:5]:
            print(f"   - {doc_id}")
        if len(failed_docs) > 5:
            print(f"   ... and {len(failed_docs) - 5} more")
    
    # Get final stats
    stats = await document_vector_store.get_stats()
    print(f"\n🗄️  Supabase Stats:")
    print(f"   Backend: {stats.get('backend')}")
    print(f"   Model: {stats.get('embedding_model')}")
    print(f"   Dimension: {stats.get('embedding_dim')}")
    print(f"   Status: {stats.get('status')}")
    
    print(f"\n✨ Migration completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    await supabase_client.disconnect()
    
    return len(failed_docs) == 0


if __name__ == "__main__":
    success = asyncio.run(migrate_documents())
    sys.exit(0 if success else 1)
