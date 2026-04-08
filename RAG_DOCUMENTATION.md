# TaxShield — Guardrailed RAG System Documentation

## Overview

This is a **pure, non-blackbox RAG (Retrieval Augmented Generation)** system built with:
- **Explicit document chunking** (transparent text splits)
- **FAISS vector store** (transparent embeddings)
- **OpenAI embeddings** (text-embedding-3-small)
- **Guardrailed LLM calling** with moderation, citations, confidence scores
- **Per-document response tracking**
- **No LangChain orchestration** (all logic is explicit and auditable)

---

## Architecture

### 1. **Document Ingestion Pipeline**

```
Document (PDF/TXT)
    ↓
[Moderation Check] ← OpenAI Moderation API
    ↓
[Chunking] ← 800 tokens/chunk, 100 token overlap
    ↓
[Embedding] ← OpenAI text-embedding-3-small
    ↓
[FAISS Index] ← Store vectors + metadata
    ↓
[Disk Persistence] ← JSON metadata + document text
```

### 2. **Query/Retrieval Pipeline**

```
User Question
    ↓
[Moderation Check] ← OpenAI Moderation API
    ↓
[Embedding] ← Same model as document chunks
    ↓
[FAISS Search] ← Cosine similarity, top-k retrieval
    ↓
[Context Building] ← Format chunks with source tags
    ↓
[LLM Call] ← GPT-4o-mini with strict system prompt
    ↓
[Response Validation] ← JSON schema, citation checks
    ↓
[Confidence Scoring] ← 0.0 (unknown) to 1.0 (certain)
```

### 3. **Guardrails & Safety**

| Layer | Mechanism | Details |
|-------|-----------|---------|
| **Input Moderation** | OpenAI Moderation API | Checks document + question for policy violations |
| **Source Citations** | Mandatory source tags | LLM must cite `doc:{id}:chunk:{idx}` |
| **JSON Validation** | Pydantic schemas | Strict response structure with typed fields |
| **Confidence Scoring** | LLM instruction | 0 = uncertain/not in docs, 1 = very confident |
| **Hallucination Prevention** | System prompt guardrails | "ONLY use provided chunks, no inference" |
| **Knowledge Cutoff** | Document-bound responses | Answers limited to uploaded documents |

---

## Module Structure

### `app/rag/vector_store.py`

**Core vector storage** with FAISS + JSON metadata.

```python
# Initialize
store = VectorStore(
    index_path="data/rag_store/faiss_index",
    metadata_path="data/rag_store/metadata.json",
    dim=1536  # OpenAI embedding dimension
)

# Add vector (called per chunk)
store.add_vector(
    embedding=np.array([...]),      # float32 array, shape (1536,)
    doc_id="circular-2023-42",      # Document identifier
    chunk_index=0,                   # Chunk sequence number
    text="Full text of chunk...",    # Original text
    source_url="https://..."        # Optional source
)

# Search
results = store.search(
    query_embedding=np.array([...]),
    top_k=5,                        # Number of results
    threshold=0.3                   # Minimum similarity (0-1)
)
# Returns: [(score, metadata), ...]

# Metadata persistence
store.save()  # Persist to disk
```

**Metadata stored per chunk:**
```json
{
  "idx": 0,
  "doc_id": "uuid-here",
  "chunk_index": 0,
  "text": "Full chunk text...",
  "source_url": "https://...",
  "embedding_model": "text-embedding-3-small",
  "created_at": "2023-11-15T10:30:00"
}
```

### `app/rag/rag_service.py`

**Guardrailed LLM service** with safety checks and structured responses.

```python
# Check input (document or question)
safe, reason = moderate_input(
    text="Some text...",
    strict=True  # Strict = flag any policy violation
)

# Embed text
embedding = call_embedding_api(
    text="Query or chunk...",
    model="text-embedding-3-small"
)

# Call LLM with guardrails
answer = call_llm_with_guard(
    context_chunks=[
        {
            "doc_id": "...",
            "chunk_index": 0,
            "text": "...",
            "source_url": "...",
            "score": 0.85,
        }
    ],
    question="What is..?",
    model="gpt-4o-mini",
    temperature=0.0,        # Deterministic
    max_tokens=1000
)
# Returns: GuardedAnswer(answer, sources, confidence, chunks_used)
```

**GuardedAnswer schema:**
```python
class GuardedAnswer(BaseModel):
    answer: str                    # The actual answer
    sources: List[str]             # Citations: ["doc:uuid:chunk:0", ...]
    confidence: float              # 0.0 (unknown) to 1.0 (very confident)
    chunks_used: List[int]         # FAISS indices of retrieved chunks
```

### `app/routes/rag_routes.py`

**FastAPI endpoints** for the RAG system.

---

## API Endpoints

### 1. **Upload Document**

**POST** `/api/rag/upload`

Upload a document and add to vector store.

**Request (multipart/form-data):**
```
file: <binary file>
title: "CBIC Circular 42/2023"
source_url: "https://cbic.gov.in/..."
document_type: "circular"  # Optional: circular, ruling, notice, etc.
```

**Response (200 OK):**
```json
{
  "doc_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "CBIC Circular 42/2023",
  "chunks_count": 12,
  "tokens_approx": 9500,
  "document_type": "circular",
  "uploaded_at": "2024-04-06T10:30:00",
  "source_url": "https://cbic.gov.in/..."
}
```

**Example (curl):**
```bash
curl -X POST http://localhost:8000/api/rag/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@circular.txt" \
  -F "title=CBIC Circular 42/2023" \
  -F "source_url=https://cbic.gov.in/..." \
  -F "document_type=circular"
```

### 2. **Query Documents**

**POST** `/api/rag/query`

Query uploaded documents with guardrailed LLM.

**Request (JSON):**
```json
{
  "question": "What is the GST ITC eligibility criteria?",
  "top_k": 5,
  "similarity_threshold": 0.3
}
```

**Response (200 OK):**
```json
{
  "question": "What is the GST ITC eligibility criteria?",
  "answer": "According to CBIC Circular 42/2023, imported goods are eligible for GST ITC if: (1) They are raw materials for manufacture of pharmaceuticals (HS Code 3004-3006), (2) Components for renewable energy systems (HS Code 8503-8504), or (3) Electronic components and semiconductors (HS Code 8542-8543). Additionally, the importer must be registered under the GST Act and must maintain documentation for 5 years.",
  "confidence": 0.95,
  "sources": [
    "doc:550e8400-e29b-41d4-a716-446655440000:chunk:0",
    "doc:550e8400-e29b-41d4-a716-446655440000:chunk:1"
  ],
  "chunks_used": [0, 1],
  "retrieved_documents": [
    {
      "doc_id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "CBIC Circular 42/2023",
      "chunks_count": 12,
      "source_url": "https://cbic.gov.in/..."
    }
  ],
  "processing_time_ms": 2450.5
}
```

### 3. **List Documents**

**GET** `/api/rag/documents`

List all uploaded documents.

**Response (200 OK):**
```json
{
  "documents": [
    {
      "doc_id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "CBIC Circular 42/2023",
      "chunks_count": 12,
      "tokens_approx": 9500,
      "document_type": "circular",
      "uploaded_at": "2024-04-06T10:30:00",
      "source_url": "https://cbic.gov.in/..."
    }
  ],
  "total_documents": 1
}
```

### 4. **Get Document**

**GET** `/api/rag/document/{doc_id}`

Retrieve full document content and metadata.

**Response (200 OK):**
```json
{
  "doc_id": "550e8400-e29b-41d4-a716-446655440000",
  "metadata": {
    "doc_id": "550e8400-e29b-41d4-a716-446655440000",
    "chunks_count": 12,
    "embedding_model": "text-embedding-3-small",
    "created_at": "2024-04-06T10:30:00",
    "source_url": "https://cbic.gov.in/..."
  },
  "content": "Full document text here..."
}
```

### 5. **Delete Document**

**DELETE** `/api/rag/document/{doc_id}`

Remove document from vector store (requires index rebuild).

**Response (200 OK):**
```json
{
  "doc_id": "550e8400-e29b-41d4-a716-446655440000",
  "chunks_deleted": 12,
  "status": "deleted"
}
```

### 6. **Store Statistics**

**GET** `/api/rag/stats`

Get vector store statistics.

**Response (200 OK):**
```json
{
  "total_documents": 5,
  "total_chunks": 60,
  "total_vectors": 60,
  "embedding_dimension": 1536,
  "index_path": "/data/rag_store/faiss_index"
}
```

---

## Configuration & Environment

### Required Environment Variables

```bash
# OpenAI API Key (for embeddings + LLM + moderation)
OPENAI_API_KEY=sk-...

# Optional: FastAPI settings
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_LLM_MODEL=gpt-4o-mini
RAG_CHUNK_SIZE=800
RAG_CHUNK_OVERLAP=100
RAG_SIMILARITY_THRESHOLD=0.3
```

### Data Directory Structure

```
data/
├── rag_store/
│   ├── faiss_index              # FAISS binary index (~100MB+ with data)
│   ├── metadata.json            # Chunk metadata (JSON)
│   └── documents/
│       ├── uuid-1.txt           # Original document text
│       ├── uuid-2.txt
│       └── ...
└── curated_kb/                  # Existing KB structure
```

---

## Usage Examples

### Python Client

```python
import requests
import json

BASE_URL = "http://localhost:8000/api/rag"
HEADERS = {"Authorization": "Bearer <your-jwt-token>"}

# 1. Upload a document
with open("circular.txt", "rb") as f:
    files = {"file": f}
    data = {
        "title": "CBIC Circular 42/2023",
        "source_url": "https://cbic.gov.in/...",
        "document_type": "circular",
    }
    resp = requests.post(f"{BASE_URL}/upload", files=files, data=data, headers=HEADERS)
    doc_id = resp.json()["doc_id"]

# 2. Query documents
payload = {
    "question": "What goods are eligible for GST ITC?",
    "top_k": 5,
    "similarity_threshold": 0.3,
}
resp = requests.post(f"{BASE_URL}/query", json=payload, headers=HEADERS)
result = resp.json()

print(f"Answer: {result['answer']}")
print(f"Confidence: {result['confidence']:.1%}")
print(f"Sources: {result['sources']}")
```

### cURL

```bash
# Upload
curl -X POST http://localhost:8000/api/rag/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@circular.txt" \
  -F "title=CBIC Circular 42/2023"

# Query
curl -X POST http://localhost:8000/api/rag/query \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What goods are eligible for GST ITC?",
    "top_k": 5
  }'

# Get statistics
curl -X GET http://localhost:8000/api/rag/stats \
  -H "Authorization: Bearer <token>"
```

### Test Script

Run the included test suite:

```bash
# Full test sequence
python backend/test_rag.py full

# Just upload
python backend/test_rag.py upload

# Query
python backend/test_rag.py query "What is the effective date?"

# Stats
python backend/test_rag.py stats
```

---

## How Guardrails Work

### 1. **Input Moderation**

Every document and question passes through OpenAI's Moderation API:

```python
response = openai_client.moderations.create(input=text)
if response.results[0].flagged:
    # Reject with reason
```

### 2. **Forced Citations**

System prompt strictly enforces:
- "ONLY use information from the provided document chunks"
- "Always cite your sources using format `doc:{id}:chunk:{idx}`"
- "If answer not in chunks, respond: 'I don't know'"

### 3. **Confidence Scoring**

LLM returns confidence 0-1:
- **0.0** = "Not in documents" or "Very uncertain"
- **0.5** = "Moderately confident"
- **1.0** = "Highly confident from multiple sources"

### 4. **JSON Schema Validation**

Response validated against Pydantic schema:

```python
class GuardedAnswer(BaseModel):
    answer: str
    sources: List[str]  # Must be valid source tags
    confidence: float   # Must be 0.0-1.0
```

Invalid responses are rejected or sanitized.

### 5. **Source Validation**

Cited sources are checked:
- Format: `doc:{id}:chunk:{index}`
- Must exist in document metadata
- Must be within chunk bounds

---

## Integration with Existing Routes

RAG system is **independent** from existing agents (Agent1-5), but can be called:

```python
# From any route
from app.rag.rag_service import call_llm_with_guard, call_embedding_api
from app.rag.vector_store import vector_store

# Example in a route
@app.get("/api/something")
async def my_route():
    # Use RAG to retrieve + answer
    answer = call_llm_with_guard(context_chunks, question)
    return {"result": answer}
```

---

## Performance Tuning

| Parameter | Default | Impact | Notes |
|-----------|---------|--------|-------|
| `chunk_size` | 800 tokens | Precision vs. coverage | Smaller = more chunks, slower but precise |
| `chunk_overlap` | 100 tokens | Boundary handling | Prevents losing info at chunk edges |
| `top_k` | 5 chunks | Context window | More chunks = higher cost, better coverage |
| `similarity_threshold` | 0.3 | Retrieval quality | Higher = fewer but more relevant results |
| `temperature` | 0.0 | Determinism | 0.0 = reproducible, 0.5+ = creative |
| `max_tokens` | 1000 | Response length | Truncates long answers |

---

## Monitoring & Logging

All operations logged to `app.logger`:

```python
logger.info(f"Uploaded doc {doc_id} with {len(chunks)} chunks")
logger.debug(f"Retrieved {len(hits)} similar chunks")
logger.warning(f"Document content flagged by moderation")
logger.error(f"LLM API call failed: {e}")
```

Check logs in:
- Stdout (during development)
- Application logs (production)

---

## Limitations & Future Improvements

| Item | Status | Notes |
|------|--------|-------|
| **FAISS rebuild on delete** | ⚠️ | Currently filters metadata only. Full rebuild needed for production scale. |
| **Embedding storage** | ⚠️ | Embeddings not persisted; regenerated on load. Store separately for speed. |
| **Multi-language** | ❌ | Currently English-only. Use `text-embedding-3-small` multilingual variant for other languages. |
| **Semantic caching** | ❌ | No caching of embeddings. Add Redis for frequently asked queries. |
| **Fine-tuned embeddings** | ❌ | Using base OpenAI model. Fine-tune on tax/regulatory domain for better precision. |
| **Hybrid search** | ❌ | Currently vector-only. Combine with BM25 for keyword matching. |

---

## Troubleshooting

### "OPENAI_API_KEY not set"
```bash
export OPENAI_API_KEY=sk-...
```

### "No similar chunks found"
- Increase `similarity_threshold` (default 0.3)
- Rephrase question
- Check documents are uploaded (`GET /api/rag/documents`)
- Verify embeddings are generated (`GET /api/rag/stats`)

### "LLM returned invalid JSON"
- Check logs for raw LLM response
- Ensure question is not too complex
- Try reducing `max_tokens` to force conciseness

### "Slow query performance"
- Reduce `top_k` (default 5)
- Optimize chunk size (balance retrieval speed vs. precision)
- Add FAISS GPU index (`faiss-gpu` package)
- Cache frequent queries

---

## Next Steps

1. **Integration with Agent5** (Verifier): Use RAG for document verification
2. **Hybrid Search**: Add BM25 for keyword + semantic search
3. **Fine-tuned Embeddings**: Train on tax/regulatory corpus
4. **Semantic Caching**: Cache embeddings in Redis
5. **Multi-modal**: Support PDFs with OCR + images
6. **Batch Upload**: Bulk document ingestion API

---

**Created:** 2024-04-06  
**Author:** TaxShield RAG Team  
**Version:** 1.0
