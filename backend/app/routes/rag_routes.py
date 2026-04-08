"""
TaxShield — RAG API Routes
Endpoints for document upload, retrieval, and guardrailed query.
"""
import os
import logging
from typing import Optional, List
from datetime import datetime
import uuid

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routes.auth import get_current_user
from app.rag.vector_store import VectorStore, chunk_text, EMBEDDING_DIM
from app.rag.rag_service import (
    call_embedding_api,
    call_llm_with_guard,
    GuardedAnswer,
    moderate_input,
)
import numpy as np

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rag", tags=["RAG"])

# Initialize vector store
RAG_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "rag_store")
os.makedirs(RAG_DATA_DIR, exist_ok=True)

FAISS_INDEX_PATH = os.path.join(RAG_DATA_DIR, "faiss_index")
METADATA_PATH = os.path.join(RAG_DATA_DIR, "metadata.json")
DOCUMENTS_DIR = os.path.join(RAG_DATA_DIR, "documents")
os.makedirs(DOCUMENTS_DIR, exist_ok=True)

vector_store = VectorStore(
    index_path=FAISS_INDEX_PATH,
    metadata_path=METADATA_PATH,
    dim=EMBEDDING_DIM,
)

# In-memory cache of documents (for production, use database)
_document_cache = {}


# ═══════════════════════════════════════════
# Request/Response Models
# ═══════════════════════════════════════════

class UploadRequest(BaseModel):
    """Request for document upload."""
    title: str = Field(description="Document title")
    source_url: Optional[str] = Field(None, description="Source URL")
    document_type: Optional[str] = Field(
        default="circular",
        description="Type: circular, ruling, notice, guidance, etc."
    )


class DocumentResponse(BaseModel):
    """Response after successful upload."""
    doc_id: str
    title: str
    chunks_count: int
    tokens_approx: int
    document_type: str
    uploaded_at: str
    source_url: Optional[str] = None


class QueryRequest(BaseModel):
    """Request for document query."""
    question: str = Field(description="Question about the documents")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve")
    similarity_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score (0-1)"
    )


class QueryResponse(BaseModel):
    """Response to query."""
    question: str
    answer: str
    confidence: float = Field(ge=0.0, le=1.0)
    sources: List[str]
    chunks_used: List[int]
    retrieved_documents: List[dict]
    processing_time_ms: float


class DocumentListResponse(BaseModel):
    """List of documents."""
    documents: List[DocumentResponse]
    total_documents: int


class StoreStatsResponse(BaseModel):
    """Vector store statistics."""
    total_documents: int
    total_chunks: int
    total_vectors: int
    embedding_dimension: int
    index_path: str


# ═══════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════

def _save_document(doc_id: str, content: str) -> str:
    """Save document content to disk."""
    path = os.path.join(DOCUMENTS_DIR, f"{doc_id}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def _load_document(doc_id: str) -> Optional[str]:
    """Load document content from disk."""
    path = os.path.join(DOCUMENTS_DIR, f"{doc_id}.txt")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return None


def _get_document_metadata(doc_id: str) -> Optional[dict]:
    """Get metadata about a document."""
    chunks = vector_store.get_document_chunks(doc_id)
    if not chunks:
        return None
    
    first = chunks[0]
    return {
        "doc_id": doc_id,
        "chunks_count": len(chunks),
        "embedding_model": first.get("embedding_model", "unknown"),
        "created_at": first.get("created_at", ""),
        "source_url": first.get("source_url", ""),
    }


# ═══════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Query(None),
    source_url: Optional[str] = Query(None),
    document_type: Optional[str] = Query("circular"),
    current_user=Depends(get_current_user),
):
    """
    Upload a document and add to vector store.
    - Reads document
    - Chunks text
    - Generates embeddings
    - Stores in FAISS + metadata
    
    Returns: doc_id, chunk count, etc.
    """
    try:
        # Read file
        content = (await file.read()).decode(errors="ignore")
        
        if not content.strip():
            raise HTTPException(status_code=400, detail="Document is empty")
        
        # Use filename or provided title
        doc_title = title or file.filename or "Untitled"
        
        # Moderate document content
        safe, reason = moderate_input(content[:2000], strict=False)  # Check first 2000 chars
        if not safe:
            logger.warning(f"Document content flagged: {reason}")
            # Continue anyway for regulatory docs, but log warning
        
        # Create doc ID
        doc_id = str(uuid.uuid4())
        
        # Save document
        _save_document(doc_id, content)
        
        # Chunk text
        chunks = chunk_text(content, chunk_size=800, overlap=100)
        if not chunks:
            raise HTTPException(status_code=400, detail="Could not chunk document")
        
        # Embed each chunk and add to vector store
        logger.info(f"Uploading doc {doc_id} with {len(chunks)} chunks")
        for chunk_idx, chunk in enumerate(chunks):
            try:
                embedding = call_embedding_api(chunk)
                embedding_array = np.array(embedding, dtype="float32")
                
                vector_store.add_vector(
                    embedding=embedding_array,
                    doc_id=doc_id,
                    chunk_index=chunk_idx,
                    text=chunk,
                    source_url=source_url,
                )
                
            except Exception as e:
                logger.error(f"Failed to embed chunk {chunk_idx}: {e}")
                # Continue with other chunks
                continue
        
        # Persist store
        vector_store.save()
        
        # Estimate tokens (rough: 1 token ~= 1.3 characters)
        tokens_approx = int(len(content) / 1.3)
        
        return DocumentResponse(
            doc_id=doc_id,
            title=doc_title,
            chunks_count=len(chunks),
            tokens_approx=tokens_approx,
            document_type=document_type,
            uploaded_at=datetime.utcnow().isoformat(),
            source_url=source_url,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/query", response_model=QueryResponse)
async def query_documents(
    req: QueryRequest,
    current_user=Depends(get_current_user),
):
    """
    Query documents with guardrailed LLM.
    - Embeds question
    - Retrieves similar chunks
    - Calls guardrailed LLM with citations
    - Returns structured answer with confidence & sources
    """
    import time
    start_time = time.time()
    
    try:
        # Moderate question
        safe, reason = moderate_input(req.question, strict=True)
        if not safe:
            raise HTTPException(status_code=400, detail=f"Question violates policy: {reason}")
        
        # Embed question
        question_embedding = call_embedding_api(req.question)
        question_array = np.array(question_embedding, dtype="float32")
        
        # Search vector store
        hits = vector_store.search(
            query_embedding=question_array,
            top_k=req.top_k,
            threshold=req.similarity_threshold,
        )
        
        if not hits:
            logger.warning(f"No similar chunks found for query: {req.question}")
            return QueryResponse(
                question=req.question,
                answer="No relevant documents found.",
                confidence=0.0,
                sources=[],
                chunks_used=[],
                retrieved_documents=[],
                processing_time_ms=0,
            )
        
        # Prepare context chunks for LLM
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
        
        logger.info(f"Retrieved {len(context_chunks)} chunks for query")
        
        # Call guardrailed LLM
        guarded_answer = call_llm_with_guard(
            context_chunks=context_chunks,
            question=req.question,
            model="gpt-4o-mini",
            temperature=0.0,
            max_tokens=1000,
        )
        
        # Load full document text for retrieved docs
        retrieved_docs = []
        seen_docs = set()
        for chunk in context_chunks:
            doc_id = chunk["doc_id"]
            if doc_id not in seen_docs:
                doc_text = _load_document(doc_id)
                doc_meta = _get_document_metadata(doc_id)
                if doc_meta:
                    retrieved_docs.append({
                        "doc_id": doc_id,
                        "title": doc_meta.get("title", "Unknown"),
                        "chunks_count": doc_meta.get("chunks_count", 0),
                        "source_url": chunk.get("source_url"),
                    })
                seen_docs.add(doc_id)
        
        processing_time_ms = (time.time() - start_time) * 1000
        
        return QueryResponse(
            question=req.question,
            answer=guarded_answer.answer,
            confidence=guarded_answer.confidence,
            sources=guarded_answer.sources,
            chunks_used=guarded_answer.chunks_used,
            retrieved_documents=retrieved_docs,
            processing_time_ms=processing_time_ms,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    current_user=Depends(get_current_user),
):
    """
    List all uploaded documents.
    """
    try:
        doc_ids = set(m["doc_id"] for m in vector_store.metadata)
        docs = []
        
        for doc_id in sorted(doc_ids):
            meta = _get_document_metadata(doc_id)
            if meta:
                docs.append(DocumentResponse(
                    doc_id=doc_id,
                    title=meta.get("title", "Unknown"),
                    chunks_count=meta["chunks_count"],
                    tokens_approx=0,  # Could calculate from stored content
                    document_type="unknown",
                    uploaded_at=meta["created_at"],
                    source_url=meta.get("source_url"),
                ))
        
        return DocumentListResponse(
            documents=docs,
            total_documents=len(docs),
        )
        
    except Exception as e:
        logger.error(f"List documents failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/document/{doc_id}")
async def get_document(
    doc_id: str,
    current_user=Depends(get_current_user),
):
    """
    Retrieve full document content and metadata.
    """
    try:
        content = _load_document(doc_id)
        if not content:
            raise HTTPException(status_code=404, detail="Document not found")
        
        meta = _get_document_metadata(doc_id)
        
        return {
            "doc_id": doc_id,
            "metadata": meta,
            "content": content,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get document failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/document/{doc_id}")
async def delete_document(
    doc_id: str,
    current_user=Depends(get_current_user),
):
    """
    Delete a document (removes from vector store and disk).
    """
    try:
        deleted_chunks = vector_store.delete_document(doc_id)
        
        # Delete file
        path = os.path.join(DOCUMENTS_DIR, f"{doc_id}.txt")
        if os.path.exists(path):
            os.remove(path)
        
        vector_store.save()
        
        return {
            "doc_id": doc_id,
            "chunks_deleted": deleted_chunks,
            "status": "deleted",
        }
        
    except Exception as e:
        logger.error(f"Delete document failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=StoreStatsResponse)
async def get_store_stats(
    current_user=Depends(get_current_user),
):
    """
    Get vector store statistics.
    """
    try:
        stats = vector_store.stats()
        return StoreStatsResponse(
            total_documents=stats["total_documents"],
            total_chunks=stats["total_chunks"],
            total_vectors=stats["total_vectors"],
            embedding_dimension=stats["embedding_dim"],
            index_path=FAISS_INDEX_PATH,
        )
    except Exception as e:
        logger.error(f"Get stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
