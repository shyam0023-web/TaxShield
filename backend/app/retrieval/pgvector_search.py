"""
TaxShield — PGVector Search Module
Purpose: Semantic similarity search using pgvector with Supabase PostgreSQL
Replaces FAISS with production-grade vector database
"""
import os
import logging
from typing import List, Dict, Optional, Tuple, Any
from app.supabase_client import supabase_client

logger = logging.getLogger(__name__)


class PGVectorSearcher:
    """
    Semantic search using Supabase pgvector.
    - Replaces FAISS for production deployments
    - Uses cosine similarity (1 - distance)
    - Supports filtering and metadata
    """
    
    def __init__(self, similarity_threshold: float = 0.3):
        """
        Initialize pgvector searcher
        
        Args:
            similarity_threshold: Minimum cosine similarity (0-1) to include results
        """
        self.similarity_threshold = similarity_threshold
        self.embedding_dim = 1536  # text-embedding-3-small
        
    async def search_similar_chunks(
        self,
        embedding: List[float],
        top_k: int = 5,
        threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar document chunks using pgvector
        
        Args:
            embedding: Query embedding vector (1536 dims for text-embedding-3-small)
            top_k: Number of results to return
            threshold: Override default similarity threshold
            
        Returns:
            List of chunks with similarity scores, sorted by relevance
        """
        if not supabase_client.is_connected:
            logger.warning("Supabase not connected for pgvector search")
            return []
        
        threshold = threshold or self.similarity_threshold
        
        try:
            # Search via Supabase RPC call (uses pgvector SQL function)
            results = await supabase_client.search_chunks_by_embedding(
                embedding=embedding,
                limit=top_k,
                similarity_threshold=threshold
            )
            
            if not results:
                logger.debug(f"No chunks found with similarity >= {threshold}")
                return []
            
            # Format results with metadata
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "chunk_id": result.get("chunk_id"),
                    "document_id": result.get("document_id"),
                    "chunk_index": result.get("chunk_index"),
                    "text": result.get("chunk_text"),
                    "similarity": result.get("similarity", 0.0),
                    "score": result.get("similarity", 0.0),  # Alias for compatibility
                })
            
            logger.debug(f"Found {len(formatted_results)} similar chunks")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching pgvector: {e}")
            return []
    
    async def get_chunk_context(
        self,
        chunk_id: int,
        context_chunks: int = 2
    ) -> Dict[str, Any]:
        """
        Get a chunk with surrounding context (previous/next chunks)
        
        Args:
            chunk_id: ID of the target chunk
            context_chunks: Number of adjacent chunks to retrieve
            
        Returns:
            Chunk with context
        """
        try:
            # This would need a custom SQL function. For now, return just the chunk
            logger.info(f"Context retrieval for chunk {chunk_id} - implement custom SQL function for production")
            return {}
        except Exception as e:
            logger.error(f"Error getting chunk context: {e}")
            return {}
    
    async def batch_search(
        self,
        embeddings: List[List[float]],
        top_k: int = 5
    ) -> List[List[Dict[str, Any]]]:
        """
        Search multiple embeddings in parallel
        
        Args:
            embeddings: List of embedding vectors
            top_k: Number of results per query
            
        Returns:
            List of result lists (one per embedding)
        """
        results = []
        for embedding in embeddings:
            result = await self.search_similar_chunks(embedding, top_k)
            results.append(result)
        return results


class DocumentVectorStore:
    """
    Manage document storage and embedding ingestion with pgvector
    Replaces the file-based VectorStore class
    """
    
    def __init__(self):
        """Initialize document vector store"""
        self.searcher = PGVectorSearcher()
    
    async def add_document(
        self,
        doc_id: str,
        title: str,
        content: str,
        source_url: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Optional[int]:
        """
        Store a document in Supabase
        
        Args:
            doc_id: Unique document identifier
            title: Document title
            content: Full document content
            source_url: Optional source URL
            metadata: Optional metadata dict
            
        Returns:
            Document ID if successful
        """
        try:
            doc = await supabase_client.get_or_create_document(
                doc_id=doc_id,
                title=title,
                content_text=content,
                source_url=source_url,
                metadata=metadata or {}
            )
            
            if doc:
                logger.info(f"✅ Added document {doc_id} (ID: {doc.get('id')})")
                return doc.get("id")
            else:
                logger.error(f"Failed to add document {doc_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error adding document: {e}")
            return None
    
    async def add_chunk_with_embedding(
        self,
        document_id: int,
        chunk_index: int,
        chunk_text: str,
        embedding: List[float],
        embedding_model: str = "text-embedding-3-small",
        bm25_metadata: Optional[Dict] = None
    ) -> bool:
        """
        Store a document chunk with its embedding vector
        
        Args:
            document_id: Parent document ID
            chunk_index: Chunk sequence number
            chunk_text: Chunk text content
            embedding: Embedding vector (1536 dims)
            embedding_model: Which model was used
            bm25_metadata: Optional BM25 scoring metadata
            
        Returns:
            True if successful
        """
        try:
            chunk = await supabase_client.add_document_chunk(
                document_id=document_id,
                chunk_index=chunk_index,
                chunk_text=chunk_text,
                embedding=embedding,
                embedding_model=embedding_model,
                bm25_metadata=bm25_metadata or {}
            )
            
            if chunk:
                return True
            else:
                logger.error(f"Failed to add chunk {chunk_index} for document {document_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error adding chunk with embedding: {e}")
            return False
    
    async def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get document by doc_id"""
        try:
            docs = await supabase_client.get_documents(limit=1)
            for doc in docs:
                if doc.get("doc_id") == doc_id:
                    return doc
            return None
        except Exception as e:
            logger.error(f"Error getting document: {e}")
            return None
    
    async def delete_document(self, doc_id: str) -> bool:
        """Delete all chunks for a document"""
        try:
            deleted = await supabase_client.delete_document_chunks(doc_id)
            if deleted > 0:
                logger.info(f"✅ Deleted {deleted} chunks for document {doc_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return False
    
    async def search(
        self,
        embedding: List[float],
        top_k: int = 5,
        threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks"""
        return await self.searcher.search_similar_chunks(embedding, top_k, threshold)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        try:
            docs = await supabase_client.get_documents(limit=1000)
            total_docs = len(docs)
            
            # This would need a better query in production
            return {
                "total_documents": total_docs,
                "backend": "Supabase pgvector",
                "embedding_model": "text-embedding-3-small",
                "embedding_dim": 1536,
                "status": "connected" if supabase_client.is_connected else "disconnected",
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"status": "error", "error": str(e)}


# Global instances
pgvector_searcher = PGVectorSearcher()
document_vector_store = DocumentVectorStore()
