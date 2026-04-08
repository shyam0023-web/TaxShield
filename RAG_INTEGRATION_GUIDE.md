# TaxShield — RAG Integration Guide

## Overview

This guide shows how to **replace blackbox LLM pipelines** with the new guardrailed RAG system while keeping existing code intact.

---

## ❌ Before (Blackbox Pipelines)

```python
# OLD: app/agents/agent3_analyst.py
from langgraph.graph import StateGraph, START, END
from app.agents.contracts import AgentState

def agent3_workflow(state: AgentState):
    """Black-box: unclear what LLM is doing internally"""
    graph = StateGraph(AgentState)
    # ... complex routing, unclear retrieval ...
    return graph.compile()

# Used like:
result = agent3.invoke({"user_input": question})  # What happened? Who knows!
```

**Problems:**
- ⚠️ No visibility into LLM behavior
- ⚠️ No citation tracking
- ⚠️ No confidence scoring
- ⚠️ No document-per-response mapping
- ⚠️ Hard to debug

---

## ✅ After (Guardrailed RAG)

```python
# NEW: Use RAG system directly
from app.rag.rag_service import call_llm_with_guard
from app.rag.vector_store import vector_store
import numpy as np
import openai

# 1. Retrieve documents
query_embedding = openai.Embedding.create(
    model="text-embedding-3-small",
    input=question
)["data"][0]["embedding"]

hits = vector_store.search(
    query_embedding=np.array(query_embedding, dtype="float32"),
    top_k=5
)

# 2. Call guardrailed LLM
context_chunks = [
    {
        "doc_id": meta["doc_id"],
        "chunk_index": meta["chunk_index"],
        "text": meta["text"],
        "source_url": meta.get("source_url"),
        "score": score,
    }
    for score, meta in hits
]

answer = call_llm_with_guard(
    context_chunks=context_chunks,
    question=question,
)

# Result is transparent & trustworthy
print(f"Answer: {answer.answer}")
print(f"Confidence: {answer.confidence}")
print(f"Sources: {answer.sources}")
```

**Benefits:**
- ✅ Clear, auditable flow
- ✅ Citation tracking
- ✅ Confidence scores
- ✅ Document mapping
- ✅ Easy to debug

---

## 🔄 Integration Path

### Option 1: Gradual Migration (Recommended)

#### Step 1: Replace Agent3 (Analyst)

**Location:** `app/agents/agent3_analyst.py`

**Before:**
```python
# LangGraph orchestration (blackbox)
def agent3_processor(state: AgentState):
    # ... unclear ...
    return state
```

**After:**
```python
from app.rag.rag_service import call_llm_with_guard
from app.rag.vector_store import vector_store
import numpy as np
import openai

def agent3_processor(state: AgentState):
    """Pure, transparent document analysis"""
    
    question = state.user_input
    
    # 1. Embed
    query_emb = openai.Embedding.create(
        model="text-embedding-3-small",
        input=question
    )["data"][0]["embedding"]
    
    # 2. Retrieve
    hits = vector_store.search(
        query_embedding=np.array(query_emb, dtype="float32"),
        top_k=5
    )
    
    if not hits:
        state.analysis = "No relevant documents found."
        state.confidence = 0.0
        return state
    
    # 3. Call guardrailed LLM
    context = [{
        "doc_id": meta["doc_id"],
        "chunk_index": meta["chunk_index"],
        "text": meta["text"],
        "source_url": meta.get("source_url"),
        "score": score,
    } for score, meta in hits]
    
    answer = call_llm_with_guard(context, question)
    
    # 4. Store results with full traceability
    state.analysis = answer.answer
    state.confidence = answer.confidence
    state.sources = answer.sources
    state.chunks_used = answer.chunks_used
    
    return state
```

#### Step 2: Update Agent State

**Location:** `app/agents/contracts.py`

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class AgentState(BaseModel):
    """Add RAG fields"""
    user_input: str
    
    # NEW RAG fields
    analysis: str = ""
    confidence: float = 0.0
    sources: List[str] = Field(default_factory=list)
    chunks_used: List[int] = Field(default_factory=list)
    retrieved_documents: List[dict] = Field(default_factory=list)
    
    # Existing fields...
    draft_text: str = ""
    verification_status: str = "pending"
```

#### Step 3: Update Routes

**Location:** `app/routes/chat.py`

**Before:**
```python
@router.post("/chat")
async def chat(msg: ChatMessage):
    # ... invoke agent3, get blackbox result ...
    return {"response": "unclear"}
```

**After:**
```python
from app.rag.rag_service import call_llm_with_guard
from app.rag.vector_store import vector_store
import numpy as np

@router.post("/chat")
async def chat(msg: ChatMessage):
    # Use RAG directly
    query_emb = openai.Embedding.create(
        model="text-embedding-3-small",
        input=msg.content
    )["data"][0]["embedding"]
    
    hits = vector_store.search(
        query_embedding=np.array(query_emb),
        top_k=5
    )
    
    context = [{
        "doc_id": m["doc_id"],
        "chunk_index": m["chunk_index"],
        "text": m["text"],
        "source_url": m.get("source_url"),
        "score": s,
    } for s, m in hits]
    
    answer = call_llm_with_guard(context, msg.content)
    
    return {
        "response": answer.answer,
        "confidence": answer.confidence,
        "sources": answer.sources,
    }
```

---

### Option 2: Parallel Deployment

Run RAG **alongside** existing agents (no refactoring needed):

**Location:** `app/routes/rag_routes.py` (already mounted)

```python
# Existing agents continue to work
# New RAG routes available at /api/rag/*
# Frontend can switch between them
```

**Frontend:**
```typescript
// Toggle between old (agent) and new (RAG)
const useRAG = true;

if (useRAG) {
  // New RAG API
  const response = await fetch("/api/rag/query", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
} else {
  // Old agent API
  const response = await fetch("/api/chat", {
    method: "POST",
    body: JSON.stringify({ user_input: question }),
  });
}
```

---

## 📋 Integration Checklist

- [ ] RAG module installed (`app/rag/` directory created)
- [ ] Dependencies added to `requirements.txt`
- [ ] `OPENAI_API_KEY` environment variable set
- [ ] RAG routes mounted in `app/main.py`
- [ ] Test upload: `curl -X POST /api/rag/upload`
- [ ] Test query: `curl -X POST /api/rag/query`
- [ ] Verify confidence scores are returned
- [ ] Verify citations are generated
- [ ] Update Agent3 state to include RAG fields
- [ ] Update routes to use `call_llm_with_guard`
- [ ] Test Agent3 → RAG integration
- [ ] Update frontend to display confidence + sources
- [ ] Run full test suite: `python test_rag.py full`

---

## 🔌 Connecting to Existing Routes

### Example: Integrate with `app/routes/notices.py`

**Scenario:** When retrieving a notice, also provide RAG-based analysis.

```python
# app/routes/notices.py
from app.rag.rag_service import call_llm_with_guard
from app.rag.vector_store import vector_store
import numpy as np

@router.get("/notices/{notice_id}/analysis")
async def get_notice_with_rag_analysis(notice_id: str):
    """Retrieve notice + RAG analysis"""
    
    # Get notice from DB
    notice = await db.get_notice(notice_id)
    
    # Generate RAG analysis
    question = f"What are the key points in this {notice.title}?"
    
    # Retrieve from vector store
    query_emb = openai.Embedding.create(
        model="text-embedding-3-small",
        input=question
    )["data"][0]["embedding"]
    
    hits = vector_store.search(np.array(query_emb, dtype="float32"), top_k=5)
    context = [{"doc_id": m["doc_id"], ...} for _, m in hits]
    
    answer = call_llm_with_guard(context, question)
    
    return {
        "notice": notice,
        "rag_analysis": {
            "summary": answer.answer,
            "confidence": answer.confidence,
            "sources": answer.sources,
        }
    }
```

---

## 🎯 Use Case Examples

### 1. Circular Analysis

```python
# New route: /api/circulars/analyze
@router.post("/circulars/analyze")
async def analyze_circular(circular_id: str, question: str):
    """Analyze CBIC circular using RAG"""
    
    # Retrieve circular chunks
    hits = vector_store.search(embed(question), top_k=10)
    
    # Call guardrailed LLM
    answer = call_llm_with_guard(hits, question)
    
    return {
        "circular_id": circular_id,
        "question": question,
        "answer": answer.answer,
        "key_points": extract_key_points(answer.answer),
        "sources": answer.sources,
        "confidence": answer.confidence,
    }
```

### 2. Ruling Lookup

```python
# New route: /api/rulings/search
@router.post("/rulings/search")
async def search_rulings(query: str):
    """Search rulings using RAG"""
    
    hits = vector_store.search(embed(query), top_k=5)
    
    return {
        "query": query,
        "results": [
            {
                "doc_id": m["doc_id"],
                "text": m["text"],
                "similarity": score,
                "source_url": m.get("source_url"),
            }
            for score, m in hits
        ]
    }
```

### 3. Draft Verification

```python
# In app/agents/agent5_verifier.py
def verify_with_rag(draft_text: str):
    """Verify draft against regulatory documents"""
    
    # Split draft into sections
    sections = draft_text.split("\n\n")
    
    verification_results = []
    for section in sections:
        # Check section against regulations
        hits = vector_store.search(embed(section), top_k=3)
        
        answer = call_llm_with_guard(
            hits,
            f"Is this compliant? {section}"
        )
        
        verification_results.append({
            "section": section,
            "compliant": answer.confidence > 0.8,
            "reasoning": answer.answer,
            "sources": answer.sources,
        })
    
    return verification_results
```

---

## 📊 Monitoring Integration

### Log RAG Usage

```python
# Add to rag_routes.py
from app.logger import logger

@router.post("/query")
async def query_documents(req: QueryRequest):
    logger.info(
        f"RAG Query | user={user_id} | question_len={len(req.question)} | "
        f"top_k={req.top_k}"
    )
    
    # ... query logic ...
    
    logger.info(
        f"RAG Answer | confidence={answer.confidence} | "
        f"sources={len(answer.sources)} | time={processing_time_ms}ms"
    )
```

### Track Metrics

```python
# app/services/rag_metrics.py
from datetime import datetime
from sqlalchemy import Column, Float, String, DateTime

class RAGQuery(Base):
    """Track RAG queries for analytics"""
    __tablename__ = "rag_queries"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, index=True)
    question = Column(String)
    answer = Column(String)
    confidence = Column(Float)
    sources_count = Column(Integer)
    processing_time_ms = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

## 🚨 Breaking Changes

### None!

RAG is **completely independent**. Existing agents/routes work unchanged.

- ✅ Existing DB queries unaffected
- ✅ Existing agent logic unaffected
- ✅ Existing routes unaffected
- ✅ Existing auth/middleware unaffected

---

## 🔧 Troubleshooting Integration

### Issue: "ImportError: No module named 'app.rag'"

**Solution:**
```bash
# Ensure directory structure exists
mkdir -p backend/app/rag
# Ensure __init__.py exists
touch backend/app/rag/__init__.py
```

### Issue: "FAISS index not found"

**Solution:**
The first upload will create it:
```bash
curl -X POST /api/rag/upload -F "file=@doc.txt"
```

### Issue: OpenAI API timeout in Agent3

**Solution:**
Reduce `top_k` and `max_tokens`:
```python
answer = call_llm_with_guard(
    context_chunks=context,
    question=question,
    max_tokens=500,  # Reduce
    model="gpt-4o-mini",  # Use faster model
)
```

---

## ✅ Validation

Test integration:

```bash
# 1. Start server
python -m uvicorn app.main:app --reload

# 2. Upload test document
curl -X POST http://localhost:8000/api/rag/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@test.txt"

# 3. Query
curl -X POST http://localhost:8000/api/rag/query \
  -H "Authorization: Bearer <token>" \
  -d '{"question": "Test"}'

# 4. Verify Agent3 still works
curl -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer <token>" \
  -d '{"user_input": "Test"}'
```

---

## 📚 Next: Fine-Tuning for Tax Domain

After integration, consider:

1. **Fine-tune embeddings** on tax/regulatory corpus
2. **Add hybrid search** (BM25 + vector)
3. **Implement caching** (Redis)
4. **Add batch processing** for bulk documents
5. **Create domain-specific prompts** for tax analysis

---

**Version:** 1.0  
**Last Updated:** 2024-04-06  
**Status:** Ready for Integration
