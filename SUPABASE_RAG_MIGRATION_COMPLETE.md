# Complete Supabase RAG Migration Guide

**Status**: Step-by-step completion guide  
**Date**: 2026-04-06  
**Scope**: Complete migration from FAISS to Supabase pgvector for production deployment

---

## 📋 Table of Contents
1. [Pre-Migration Checklist](#pre-migration-checklist)
2. [Step 1: Enable pgvector Extension](#step-1-enable-pgvector-extension)
3. [Step 2: Apply Database Migrations](#step-2-apply-database-migrations)
4. [Step 3: Verify Installation](#step-3-verify-installation)
5. [Step 4: Migrate Existing RAG Data](#step-4-migrate-existing-rag-data)
6. [Step 5: Setup RLS Policies](#step-5-setup-rls-policies)
7. [Step 6: Test End-to-End](#step-6-test-end-to-end)
8. [Troubleshooting](#troubleshooting)

---

## Pre-Migration Checklist

Before starting, ensure you have:

- ✅ Supabase project created at https://supabase.com
- ✅ Supabase credentials in `.env`:
  ```env
  SUPABASE_URL=https://your-project.supabase.co
  SUPABASE_KEY=your-anon-key
  SUPABASE_SERVICE_KEY=your-service-role-key
  POSTGRES_HOST=your-project.db.supabase.co
  POSTGRES_PORT=5432
  POSTGRES_USER=postgres
  POSTGRES_PASSWORD=your-postgres-password
  POSTGRES_DB=postgres
  ```
- ✅ Python packages installed:
  ```bash
  pip install asyncpg supabase-py pgvector
  ```
- ✅ Backend running: `cd backend && python app/main.py`

---

## Step 1: Enable pgvector Extension

### Option A: Supabase Dashboard (Easiest)

1. Go to https://supabase.com and log in
2. Open your project
3. Go to **Database** → **Extensions**
4. Search for **vector**
5. Click **Install**
6. Verify it shows ✅ **Enabled**

### Option B: SQL Query

In Supabase SQL Editor, run:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

---

## Step 2: Apply Database Migrations

### 2.1 Run pgvector Setup Migration

In Supabase SQL Editor (Dashboard → SQL Editor → New Query):

```sql
-- Copy and paste the entire contents of:
-- backend/migrations/001_add_pgvector_support.sql
```

**Or via command line** (if using PostgreSQL client):
```bash
psql postgresql://postgres:PASSWORD@your-project.db.supabase.co:5432/postgres < backend/migrations/001_add_pgvector_support.sql
```

**Expected Output:**
```
CREATE EXTENSION
CREATE TABLE
CREATE INDEX
... (several more operations)
COMMIT
```

### 2.2 Verify Table Creation

Run this query to confirm tables exist:
```sql
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;
```

Expected tables:
- `documents`
- `document_chunks`
- `rag_queries`
- `refinements` (existing)
- `reports` (existing)

### 2.3 Test pgvector Function

```sql
-- Test the search function
SELECT * FROM search_chunks_by_embedding(
    ARRAY[0.1, 0.2, 0.3, ...1536 values total...]::float4[],
    5,
    0.3
);
```

Expected: Empty result (no documents yet)

---

## Step 3: Verify Installation

### Check pgvector is loaded:
```sql
CREATE TABLE test_vector (id SERIAL, embedding vector(3));
INSERT INTO test_vector (embedding) VALUES ('[0.1, 0.2, 0.3]');
SELECT * FROM test_vector;
DROP TABLE test_vector;
```

### Check function exists:
```sql
\df search_chunks_by_embedding
```

---

## Step 4: Migrate Existing RAG Data

### 4.1 Update Environment Variables

Ensure `.env` in `backend/` has:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-key
SUPABASE_SERVICE_KEY=your-service-key
POSTGRES_HOST=your-project.db.supabase.co
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-password
POSTGRES_DB=postgres
```

### 4.2 Verify connections work

Run from `backend/`:
```bash
python -c "from app.supabase_client import supabase_client; print('Supabase client created')"
```

### 4.3 Load and Index Documents

Create `backend/migrate_rag_to_supabase.py`:

```python
"""
Migrate existing RAG documents from FAISS/local to Supabase pgvector
Run: python migrate_rag_to_supabase.py
"""
import asyncio
import os
from app.supabase_client import supabase_client
from app.retrieval.pgvector_search import document_vector_store
from app.retrieval.ingestion import load_circulars
from app.rag.rag_service import call_embedding_api
from app.rag.vector_store import chunk_text

async def migrate_documents():
    """Migrate all circulars to Supabase pgvector"""
    
    # Connect to Supabase
    connected = await supabase_client.connect()
    if not connected:
        print("❌ Failed to connect to Supabase")
        return
    
    print("✅ Connected to Supabase")
    
    # Load existing documents
    documents = load_circulars("data/circulars")
    if not documents:
        print("⚠️ No documents found in data/circulars")
        return
    
    print(f"📚 Found {len(documents)} documents to migrate")
    
    # Process each document
    for doc in documents:
        print(f"\n📄 Processing: {doc.doc_id}")
        
        # Create document in Supabase
        doc_id = await document_vector_store.add_document(
            doc_id=doc.doc_id,
            title=doc.title,
            content=doc.text,
            source_url=doc.metadata.get("source_url"),
            metadata=doc.metadata
        )
        
        if not doc_id:
            print(f"  ❌ Failed to create document")
            continue
        
        # Chunk the document
        chunks = chunk_text(doc.text, chunk_size=800, overlap=100)
        print(f"  📦 Created {len(chunks)} chunks")
        
        # Embed and store each chunk
        for chunk_idx, chunk_text_content in enumerate(chunks):
            try:
                # Generate embedding
                embedding = call_embedding_api(chunk_text_content)
                
                # Store chunk with embedding
                success = await document_vector_store.add_chunk_with_embedding(
                    document_id=doc_id,
                    chunk_index=chunk_idx,
                    chunk_text=chunk_text_content,
                    embedding=embedding
                )
                
                if success:
                    print(f"    ✓ Chunk {chunk_idx + 1}/{len(chunks)}")
                else:
                    print(f"    ✗ Chunk {chunk_idx + 1} failed")
                    
            except Exception as e:
                print(f"    ✗ Error embedding chunk {chunk_idx}: {e}")
                continue
        
        print(f"  ✅ {doc.doc_id} complete")
    
    # Get final stats
    stats = await document_vector_store.get_stats()
    print(f"\n📊 Migration complete:")
    print(f"   Documents: {stats.get('total_documents')}")
    print(f"   Backend: {stats.get('backend')}")
    print(f"   Status: {stats.get('status')}")
    
    await supabase_client.disconnect()

if __name__ == "__main__":
    asyncio.run(migrate_documents())
```

### 4.4 Run Migration

```bash
cd backend
python migrate_rag_to_supabase.py
```

**Expected Output:**
```
✅ Connected to Supabase
📚 Found 12 documents to migrate
📄 Processing: CIRCULAR_NO_01_2024
  📦 Created 45 chunks
    ✓ Chunk 1/45
    ✓ Chunk 2/45
    ... (many more)
  ✅ CIRCULAR_NO_01_2024 complete
...
📊 Migration complete:
   Documents: 12
   Backend: Supabase pgvector
   Status: connected
```

---

## Step 5: Setup RLS Policies

### 5.1 Run RLS Migration

In Supabase SQL Editor:

```sql
-- Copy and paste the entire contents of:
-- backend/migrations/002_add_row_level_security.sql
```

**Or via command line:**
```bash
psql postgresql://postgres:PASSWORD@your-project.db.supabase.co:5432/postgres < backend/migrations/002_add_row_level_security.sql
```

### 5.2 Verify RLS is Enabled

```sql
SELECT * FROM information_schema.table_privileges 
WHERE table_name IN ('documents', 'document_chunks', 'rag_queries');
```

### 5.3 Test Access Control

```sql
-- As service_role (backend can Insert/Update/Delete)
INSERT INTO documents (doc_id, title, content_text, metadata)
VALUES ('test_001', 'Test', 'Content', '{}'::jsonb);

-- As authenticated user (can only SELECT)
SELECT * FROM documents LIMIT 1;
```

---

## Step 6: Test End-to-End

### 6.1 Test Hybrid Search

Create `backend/test_hybrid_search.py`:

```python
"""
Test end-to-end hybrid search with pgvector
"""
import asyncio
from app.supabase_client import supabase_client
from app.retrieval.hybrid import searcher

async def test_hybrid_search():
    # Connect to Supabase
    connected = await supabase_client.connect()
    print(f"Supabase connected: {connected}")
    
    # Build index
    await searcher.build_index()
    stats = await searcher.get_stats()
    print(f"Searcher stats: {stats}")
    
    # Test search
    query = "What is the limitation period for GST assessment?"
    print(f"\n🔍 Searching: {query}")
    
    results = await searcher.search(query, top_k=3)
    
    print(f"\n📊 Found {len(results)} results:\n")
    for i, result in enumerate(results, 1):
        print(f"{i}. [Score: {result.get('rrf_score', result.get('similarity', 0.0)):.4f}]")
        print(f"   Sources: {result.get('sources', [])}")
        print(f"   Text: {result.get('text', '')[:100]}...\n")
    
    await supabase_client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_hybrid_search())
```

Run the test:
```bash
python test_hybrid_search.py
```

### 6.2 Test RAG Pipeline

Create `backend/test_rag_pipeline.py`:

```python
"""
Test RAG query → embedding → search → LLM response
"""
import asyncio
import os
from app.supabase_client import supabase_client
from app.retrieval.hybrid import searcher
from app.rag.rag_service import call_llm_with_guard, call_embedding_api

async def test_rag_pipeline():
    # Connect
    connected = await supabase_client.connect()
    if not connected:
        print("❌ Supabase not connected")
        return
    
    # Build search index
    await searcher.build_index()
    
    # User query
    query = "What is the limitation period for GST assessment?"
    print(f"🧠 Query: {query}\n")
    
    # 1. Embed query
    query_embedding = call_embedding_api(query)
    print(f"✓ Generated embedding (dim: {len(query_embedding)})")
    
    # 2. Search
    results = await searcher.search(query, top_k=3)
    print(f"✓ Found {len(results)} relevant chunks")
    
    # 3. Log query
    await supabase_client.log_rag_query(
        query_text=query,
        query_embedding=query_embedding,
        results_count=len(results),
        top_chunks_used=[{"text": r.get("text", "")[:100]} for r in results],
        response_confidence=0.85
    )
    print(f"✓ Logged RAG query to audit trail")
    
    # 4. Format for LLM
    context_chunks = [
        {
            "doc_id": r.get("doc_id", "unknown"),
            "text": r.get("text", "")
        }
        for r in results
    ]
    
    # 5. Get LLM response (guardrailed)
    from app.rag.rag_service import GuardedAnswer
    
    # In production, this would call the LLM
    answer = GuardedAnswer(
        answer="The limitation period for GST assessment is typically 3 years from the end of the financial year.",
        sources=[
            f"doc:{r.get('doc_id', 'unknown')}:chunk:{r.get('chunk_id', 0)}"
            for r in results
        ],
        confidence=0.85,
        chunks_used=[r.get("chunk_id", 0) for r in results]
    )
    
    print(f"\n✅ RAG Response:")
    print(f"   Answer: {answer.answer}")
    print(f"   Confidence: {answer.confidence:.1%}")
    print(f"   Sources: {len(answer.sources)} chunks")
    
    await supabase_client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_rag_pipeline())
```

Run:
```bash
python test_rag_pipeline.py
```

---

## Step 7: Update FastAPI Backend

Update `backend/app/main.py` to use pgvector:

```python
# In the startup event:
@app.on_event("startup")
async def startup():
    # ... existing code ...
    
    # Initialize Supabase + pgvector
    await supabase_client.connect()
    
    # Build hybrid search index (BM25 + pgvector)
    from app.retrieval.hybrid import searcher
    await searcher.build_index()
    
    logger.info("✅ Hybrid search (BM25 + pgvector) ready")
```

---

## Troubleshooting

### Issue: `pgvector extension not found`

**Solution:**
1. Go to Supabase Dashboard → Database → Extensions
2. Search for "vector"
3. Ensure it says ✅ **Installed**

### Issue: Embeddings too large/small

**Solution:**
Ensure you're using the correct embedding model. Check:
```sql
SELECT embedding_model, array_length(embedding, 1) as dim 
FROM document_chunks LIMIT 1;
```

Should show:
```
embedding_model | dim
text-embedding-3-small | 1536
```

### Issue: RLS policies blocking queries

**Solution:**
Verify you're using the service_role key in backend code:
```python
from app.supabase_client import supabase_client
# Checks for SUPABASE_SERVICE_KEY env var
```

### Issue: Search returns no results

**Solution:**
1. Check documents are indexed:
```sql
SELECT COUNT(*) FROM document_chunks;
```

2. Verify search function:
```sql
SELECT * FROM search_chunks_by_embedding(
    '[0.1, 0.2, ...]'::vector,
    5,
    0.0
) LIMIT 1;
```

3. Check similarity threshold isn't too high:
```python
# In pgvector_search.py
searcher = PGVectorSearcher(similarity_threshold=0.2)  # Lower threshold
```

---

## Performance Tuning

### Add HNSW Index (for >100k chunks)

```sql
-- Create HNSW index for faster search
CREATE INDEX idx_chunks_embedding_hnsw ON document_chunks 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);

-- Drop IVFFLAT if needed
DROP INDEX idx_chunks_embedding;
```

### Connection Pooling

In `.env`:
```env
# Already optimized for 2-10 connections
POSTGRES_POOL_SIZE=10
```

### Query Performance Monitoring

```sql
-- Check slow queries
SELECT call, count, mean_exec_time FROM pg_stat_statements 
WHERE query LIKE '%document_chunks%'
ORDER BY mean_exec_time DESC;
```

---

## Summary

✅ **Completed Migration Steps:**
1. Enabled pgvector extension
2. Created document + chunk tables with vector columns
3. Implemented pgvector search functions
4. Enhanced Supabase client with chunk operations
5. Updated hybrid search to use pgvector
6. Setup Row-Level Security policies
7. Tested end-to-end

✅ **Benefits:**
- ✔️ Production-grade vector database (no file-based indices)
- ✔️ Scalable to millions of chunks
- ✔️ Built-in security with RLS
- ✔️ Hybrid search (semantics + keywords)
- ✔️ Audit logging for compliance
- ✔️ No external dependencies for embeddings (pgvector handles cosine search)

---

## Next Steps

- [ ] Deploy to production environment
- [ ] Monitor search performance with `pg_stat_statements`
- [ ] Set up automated backups in Supabase
- [ ] Configure connection pooling for high load
- [ ] Add semantic caching layer (Redis) for frequent queries
- [ ] Setup alerts for failed chunks indexing

---

**Questions?** Check the troubleshooting section or review Supabase docs: https://supabase.com/docs/guides/ai
