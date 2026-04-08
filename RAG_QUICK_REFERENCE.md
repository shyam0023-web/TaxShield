# TaxShield RAG System — Quick Reference

## ⚡ Quick Start (5 minutes)

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Set Environment
```bash
export OPENAI_API_KEY=sk-...
```

### 3. Verify Setup
```bash
python ../verify_rag_setup.py
```

### 4. Start Backend
```bash
python -m uvicorn app.main:app --reload
```

### 5. Test RAG
```bash
# In another terminal
python test_rag.py full
```

---

## 📋 API Quick Reference

### Upload Document
```bash
curl -X POST http://localhost:8000/api/rag/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@document.txt" \
  -F "title=My Document" \
  -F "source_url=https://..."
```

### Query Documents
```bash
curl -X POST http://localhost:8000/api/rag/query \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the GST ITC eligibility?",
    "top_k": 5,
    "similarity_threshold": 0.3
  }'
```

### List Documents
```bash
curl -X GET http://localhost:8000/api/rag/documents \
  -H "Authorization: Bearer <token>"
```

### Get Statistics
```bash
curl -X GET http://localhost:8000/api/rag/stats \
  -H "Authorization: Bearer <token>"
```

---

## 🏗️ Architecture at a Glance

```
Document → Chunk → Embed → FAISS Store
                                ↓
Question → Embed → Search → LLM (with guardrails) → Answer + Sources
```

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| **Vector Store** | `app/rag/vector_store.py` | FAISS indexing + metadata persistence |
| **LLM Service** | `app/rag/rag_service.py` | Guardrailed LLM calls, moderation, citations |
| **API Routes** | `app/routes/rag_routes.py` | FastAPI endpoints for RAG operations |

---

## 🛡️ Guardrails Overview

| Guardrail | Mechanism |
|-----------|-----------|
| **Input Check** | OpenAI Moderation API (docs & questions) |
| **Chunking** | Explicit text splitting (800 tokens, 100 overlap) |
| **Embedding** | OpenAI text-embedding-3-small |
| **Retrieval** | FAISS cosine similarity search |
| **LLM Prompt** | Strict system instructions to cite sources only |
| **Response Validation** | Pydantic JSON schema + source verification |
| **Confidence Score** | LLM confidence 0.0 (unknown) to 1.0 (certain) |

---

## 📊 Data Structure

### Document Metadata
```json
{
  "doc_id": "uuid",
  "chunk_index": 0,
  "text": "Chunk text...",
  "source_url": "https://...",
  "embedding_model": "text-embedding-3-small",
  "created_at": "2024-04-06T10:30:00"
}
```

### Query Response
```json
{
  "answer": "The answer based on documents...",
  "confidence": 0.95,
  "sources": ["doc:uuid:chunk:0", "doc:uuid:chunk:1"],
  "chunks_used": [0, 1],
  "processing_time_ms": 2450
}
```

---

## 🔧 Common Operations

### In Python Code

```python
from app.rag.rag_service import call_llm_with_guard
from app.rag.vector_store import vector_store, chunk_text
import numpy as np

# Load documents
store = vector_store

# Chunk & embed
chunks = chunk_text(document_text)
for i, chunk in enumerate(chunks):
    embedding = call_embedding_api(chunk)
    store.add_vector(
        embedding=np.array(embedding),
        doc_id="doc-123",
        chunk_index=i,
        text=chunk
    )

# Query
results = store.search(query_embedding, top_k=5)
answer = call_llm_with_guard(results, question)
print(f"Answer: {answer.answer}")
print(f"Confidence: {answer.confidence}")
```

---

## ⚙️ Configuration Parameters

| Parameter | Default | Location |
|-----------|---------|----------|
| Chunk size | 800 tokens | `vector_store.chunk_text()` |
| Chunk overlap | 100 tokens | `vector_store.chunk_text()` |
| Embedding model | text-embedding-3-small | `rag_service.call_embedding_api()` |
| LLM model | gpt-4o-mini | `rag_routes.query_documents()` |
| Temperature | 0.0 (deterministic) | `rag_service.call_llm_with_guard()` |
| Max tokens | 1000 | `rag_service.call_llm_with_guard()` |
| Top-k retrieval | 5 | `rag_routes.QueryRequest.top_k` |
| Similarity threshold | 0.3 | `rag_routes.QueryRequest.similarity_threshold` |

---

## 🐛 Troubleshooting

### Issue: "OPENAI_API_KEY not set"
**Solution:**
```bash
export OPENAI_API_KEY=sk-...
```

### Issue: "No similar chunks found"
**Solutions:**
1. Check documents uploaded: `GET /api/rag/documents`
2. Rephrase question to match document terminology
3. Lower `similarity_threshold` in query (e.g., 0.2)
4. Increase `top_k` to retrieve more chunks

### Issue: "Module not found" errors
**Solution:**
```bash
cd backend
pip install -r requirements.txt
```

### Issue: Slow queries
**Solutions:**
1. Reduce `top_k` (default 5)
2. Optimize chunk size (smaller = faster but less context)
3. Cache frequent queries
4. Use FAISS GPU index (`pip install faiss-gpu`)

---

## 📁 File Structure

```
backend/
├── app/
│   ├── rag/                    ← NEW
│   │   ├── __init__.py
│   │   ├── vector_store.py    ← FAISS + metadata
│   │   └── rag_service.py     ← Guardrailed LLM
│   ├── routes/
│   │   └── rag_routes.py      ← API endpoints (MOVED)
│   └── main.py                ← Updated with rag_routes
├── data/
│   └── rag_store/             ← NEW
│       ├── faiss_index
│       ├── metadata.json
│       └── documents/
├── requirements.txt           ← Updated
├── test_rag.py               ← NEW
└── verify_rag_setup.py       ← NEW (root dir)
```

---

## ✅ What's Included

- ✅ Pure, non-blackbox RAG implementation
- ✅ FAISS vector search with OpenAI embeddings
- ✅ Guardrailed LLM calling with citations
- ✅ Input moderation (documents + questions)
- ✅ Confidence scoring (0-1)
- ✅ Per-document response tracking
- ✅ FastAPI endpoints with proper schemas
- ✅ Full documentation
- ✅ Test suite

## ❌ What's NOT Included (Future Work)

- ❌ Hybrid search (BM25 + vector)
- ❌ Multi-language support
- ❌ Fine-tuned embeddings
- ❌ Semantic caching
- ❌ PDF/OCR support
- ❌ Batch upload API

---

## 📚 Documentation

- **Full docs**: `RAG_DOCUMENTATION.md`
- **API examples**: `test_rag.py`
- **Setup verification**: `verify_rag_setup.py`

---

## 🚀 Next Steps

1. **Integrate with Agent5**: Use RAG for document verification
2. **Add Hybrid Search**: Combine vector + keyword search
3. **Fine-tune Embeddings**: Train on tax/regulatory data
4. **Cache Queries**: Redis caching for frequent queries
5. **Monitor & Log**: Track query patterns, confidence trends

---

**Version:** 1.0  
**Last Updated:** 2024-04-06  
**Status:** Production-Ready
