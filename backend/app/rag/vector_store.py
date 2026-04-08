"""
TaxShield — Vector Store Module
Pure explicit RAG: FAISS + OpenAI embeddings with metadata persistence.
No LangChain blackbox.
"""
import os
import json
import faiss
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 1536  # text-embedding-3-small dimension


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """
    Split text into overlapping chunks by token count (word-based approximation).
    
    Args:
        text: Input document text
        chunk_size: Tokens per chunk (approx. words)
        overlap: Overlap between chunks
        
    Returns:
        List of chunk strings
    """
    tokens = text.split()
    if len(tokens) <= chunk_size:
        return [text]
    
    chunks = []
    i = 0
    while i < len(tokens):
        end = min(i + chunk_size, len(tokens))
        chunk = " ".join(tokens[i:end])
        chunks.append(chunk)
        i = end - overlap
        if i <= 0:
            break
    
    return chunks if chunks else [text]


class VectorStore:
    """
    FAISS-backed vector store with JSON metadata persistence.
    Tracks: doc_id, chunk_index, text, embedding_model, created_at
    """
    
    def __init__(
        self,
        index_path: str,
        metadata_path: str,
        dim: int = EMBEDDING_DIM,
    ):
        """
        Initialize or load vector store.
        
        Args:
            index_path: Path to save/load FAISS index
            metadata_path: Path to save/load metadata JSON
            dim: Embedding dimension (default: 1536 for OpenAI)
        """
        self.index_path = index_path
        self.metadata_path = metadata_path
        self.dim = dim
        
        # Create directory if needed
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        
        # Load or create FAISS index
        if os.path.exists(index_path):
            self.index = faiss.read_index(index_path)
            logger.info(f"Loaded FAISS index from {index_path} ({self.index.ntotal} vectors)")
        else:
            # InnerProduct for cosine similarity (if normalized)
            self.index = faiss.IndexFlatIP(dim)
            logger.info(f"Created new FAISS index (dim={dim})")
        
        # Load or create metadata
        if os.path.exists(metadata_path):
            with open(metadata_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
            logger.info(f"Loaded {len(self.metadata)} metadata entries")
        else:
            self.metadata = []
    
    def add_vector(
        self,
        embedding: np.ndarray,
        doc_id: str,
        chunk_index: int,
        text: str,
        source_url: Optional[str] = None,
    ) -> int:
        """
        Add a vector to the store.
        
        Args:
            embedding: numpy array, shape (dim,)
            doc_id: Document identifier
            chunk_index: Chunk sequence number
            text: Original chunk text
            source_url: Optional source URL
            
        Returns:
            Index in the FAISS store
        """
        # Validate & normalize embedding
        if embedding.shape[0] != self.dim:
            # Pad or truncate
            arr = np.zeros(self.dim, dtype="float32")
            copy_len = min(self.dim, embedding.shape[0])
            arr[:copy_len] = embedding[:copy_len]
            embedding = arr
        else:
            embedding = embedding.astype("float32")
        
        # L2 normalize for cosine similarity
        embedding = embedding.reshape(1, -1)
        faiss.normalize_L2(embedding)
        
        # Add to FAISS
        self.index.add(embedding)
        idx = self.index.ntotal - 1
        
        # Store metadata
        meta = {
            "idx": idx,
            "doc_id": doc_id,
            "chunk_index": chunk_index,
            "text": text,
            "source_url": source_url,
            "embedding_model": "text-embedding-3-small",
            "created_at": datetime.utcnow().isoformat(),
        }
        self.metadata.append(meta)
        
        return idx
    
    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        threshold: float = 0.3,
    ) -> List[Tuple[float, Dict[str, Any]]]:
        """
        Search for similar vectors.
        
        Args:
            query_embedding: Query embedding (dim,)
            top_k: Number of results
            threshold: Minimum similarity score (0-1)
            
        Returns:
            List of (similarity_score, metadata) tuples
        """
        if self.index.ntotal == 0:
            logger.warning("Vector store is empty")
            return []
        
        # Normalize query
        q = query_embedding.astype("float32").reshape(1, -1)
        faiss.normalize_L2(q)
        
        k = min(top_k, self.index.ntotal)
        distances, indices = self.index.search(q, k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:  # Invalid result
                continue
            score = float(dist)
            if score < threshold:
                continue
            
            meta = self.metadata[idx]
            results.append((score, meta))
        
        return results
    
    def get_document_chunks(self, doc_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all chunks for a document.
        
        Args:
            doc_id: Document identifier
            
        Returns:
            List of metadata dicts for chunks in this doc
        """
        return [m for m in self.metadata if m["doc_id"] == doc_id]
    
    def delete_document(self, doc_id: str) -> int:
        """
        Mark chunks as deleted (simple approach: filter on retrieval).
        For full FAISS deletion, rebuild index.
        
        Args:
            doc_id: Document to delete
            
        Returns:
            Number of chunks deleted
        """
        before = len(self.metadata)
        self.metadata = [m for m in self.metadata if m["doc_id"] != doc_id]
        deleted = before - len(self.metadata)
        
        if deleted > 0:
            self._rebuild_index()
            logger.info(f"Deleted {deleted} chunks from {doc_id}")
        
        return deleted
    
    def _rebuild_index(self):
        """
        Rebuild FAISS index from scratch (needed after metadata deletion).
        """
        old_index = self.index
        self.index = faiss.IndexFlatIP(self.dim)
        
        # Re-add all vectors (you'd need to store them separately for production)
        logger.warning("Index rebuild requires re-embedding. For production, store embeddings.")
    
    def save(self):
        """Persist FAISS index and metadata to disk."""
        faiss.write_index(self.index, self.index_path)
        with open(self.metadata_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)
        logger.info(f"Saved vector store: {self.index_path}, {len(self.metadata)} metadata entries")
    
    def stats(self) -> Dict[str, Any]:
        """Return store statistics."""
        doc_ids = set(m["doc_id"] for m in self.metadata)
        return {
            "total_vectors": self.index.ntotal,
            "total_documents": len(doc_ids),
            "total_chunks": len(self.metadata),
            "embedding_dim": self.dim,
        }
