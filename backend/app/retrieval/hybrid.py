"""
TaxShield — Hybrid Search (BM25 + pgvector with RRF Fusion)
Pipeline: BM25 (keyword) + pgvector (semantic on Supabase) → RRF fusion → top_k

Upgraded from FAISS to Supabase pgvector for production scalability.
Maintains cosine similarity + BM25 scores fused via Reciprocal Rank Fusion.
"""
import numpy as np
import re
import logging
import asyncio
from typing import List, Dict, Optional, Any
from rank_bm25 import BM25Okapi
from app.retrieval.ingestion import load_circulars, LegalDocument
from app.retrieval.pgvector_search import pgvector_searcher

logger = logging.getLogger(__name__)

# Search defaults
EMBEDDING_MODEL = "text-embedding-3-small"  # Must match pgvector embeddings
PGVECTOR_K = 10   # Top-k candidates from pgvector
BM25_K = 10       # Top-k candidates from BM25
RRF_K = 60        # RRF fusion parameter


def simple_tokenize(text: str) -> List[str]:
    """Tokenize text for BM25"""
    return re.findall(r"\w+", text.lower())


class HybridSearcher:
    """
    Hybrid search combining BM25 (keyword) and pgvector (semantic).
    
    - BM25: Fast keyword matching with IDF weighting
    - pgvector: Semantic similarity via Supabase
    - RRF: Reciprocal Rank Fusion for result merging
    """
    
    def __init__(self):
        """Initialize hybrid searcher"""
        self.documents: List[LegalDocument] = []
        self.bm25: Optional[BM25Okapi] = None
        self._embedding_client = None
        self.pgvector_ready = False
    
    @property
    def embedding_client(self):
        """Lazy-load OpenAI embedding client"""
        if self._embedding_client is None:
            import openai
            import os
            self._embedding_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        return self._embedding_client
    
    def _init_bm25(self):
        """Initialize BM25 index from documents"""
        tokenized_corpus = [simple_tokenize(doc.text) for doc in self.documents]
        self.bm25 = BM25Okapi(tokenized_corpus)
        logger.info(f"✅ Initialized BM25 with {len(self.documents)} documents")
    
    async def build_index(self):
        """
        Build search indices.
        
        For pgvector: Documents are stored in Supabase (no rebuild needed)
        For BM25: Initialize from loaded documents
        """
        logger.info("Building hybrid search index...")
        
        # Load documents
        self.documents = load_circulars()
        if not self.documents:
            logger.warning("⚠️ No documents loaded for indexing!")
            return
        
        # Initialize BM25
        self._init_bm25()
        
        logger.info(f"✅ Hybrid index ready: {len(self.documents)} documents, pgvector on Supabase")
        self.pgvector_ready = True
    
    async def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Hybrid search: BM25 + pgvector → RRF fusion → top_k
        
        Args:
            query: Search query text
            top_k: Number of results to return
            
        Returns:
            List of results with scores and metadata
        """
        if not self.documents:
            logger.warning("No documents to search")
            return []
        
        # ═══ Stage 1: pgvector semantic search ═══
        pgvector_results = await self._search_pgvector(query, PGVECTOR_K)
        
        # ═══ Stage 2: BM25 keyword search ═══
        bm25_results = self._search_bm25(query, BM25_K)
        
        # ═══ Stage 3: RRF fusion ═══
        final_results = self._rrf_fusion(pgvector_results, bm25_results, top_k)
        
        logger.info(f"Hybrid search found {len(final_results)} results (pgvector: {len(pgvector_results)}, BM25: {len(bm25_results)})")
        return final_results
    
    async def _search_pgvector(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search using pgvector semantic similarity
        
        Args:
            query: Search query
            limit: Max results to return
            
        Returns:
            List of results with similarity scores
        """
        try:
            # Generate embedding for query
            embedding = self._get_embedding(query)
            if not embedding:
                logger.warning("Failed to generate query embedding")
                return []
            
            # Search via pgvector
            results = await pgvector_searcher.search_similar_chunks(
                embedding=embedding,
                top_k=limit,
                threshold=0.2
            )
            
            # Convert to format compatible with RRF
            formatted = []
            for result in results:
                formatted.append({
                    "doc_id": None,  # Will map from chunk
                    "chunk_id": result.get("chunk_id"),
                    "text": result.get("text", result.get("chunk_text")),
                    "similarity": result.get("similarity", result.get("score", 0.0)),
                    "source": "pgvector",
                })
            
            return formatted
        except Exception as e:
            logger.error(f"pgvector search failed: {e}")
            return []
    
    def _search_bm25(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search using BM25 keyword matching
        
        Args:
            query: Search query
            limit: Max results to return
            
        Returns:
            List of results with BM25 scores
        """
        try:
            if not self.bm25:
                logger.warning("BM25 not initialized")
                return []
            
            # Tokenize query
            tokenized_query = simple_tokenize(query)
            
            # Get BM25 scores
            bm25_scores = self.bm25.get_scores(tokenized_query)
            
            # Get top-k indices
            top_indices = np.argsort(bm25_scores)[-limit:][::-1]
            
            results = []
            for rank, idx in enumerate(top_indices):
                if idx < 0 or idx >= len(self.documents):
                    continue
                
                score = float(bm25_scores[idx])
                if score <= 0:
                    continue
                
                doc = self.documents[idx]
                results.append({
                    "doc_id": doc.doc_id,
                    "text": doc.text,
                    "bm25_score": score,
                    "source": "bm25",
                })
            
            return results
        except Exception as e:
            logger.error(f"BM25 search failed: {e}")
            return []
    
    def _rrf_fusion(self, pgvector_results: List[Dict], 
                   bm25_results: List[Dict], 
                   top_k: int = 5) -> List[Dict]:
        """
        Fuse pgvector and BM25 results using Reciprocal Rank Fusion
        
        Args:
            pgvector_results: Semantic search results
            bm25_results: Keyword search results
            top_k: Number of final results
            
        Returns:
            Merged and ranked results
        """
        # Build ranking dictionaries
        pgvector_ranks = {i: result for i, result in enumerate(pgvector_results)}
        bm25_ranks = {i: result for i, result in enumerate(bm25_results)}
        
        # Map documents to results
        doc_to_score = {}
        
        # Add pgvector scores
        for rank, result in pgvector_ranks.items():
            doc_key = result.get("doc_id") or result.get("chunk_id")
            if doc_key not in doc_to_score:
                doc_to_score[doc_key] = {"result": result, "score": 0, "sources": []}
            doc_to_score[doc_key]["score"] += 1 / (RRF_K + rank)
            doc_to_score[doc_key]["sources"].append("pgvector")
        
        # Add BM25 scores
        for rank, result in bm25_ranks.items():
            doc_key = result.get("doc_id")
            if doc_key not in doc_to_score:
                doc_to_score[doc_key] = {"result": result, "score": 0, "sources": []}
            doc_to_score[doc_key]["score"] += 1 / (RRF_K + rank)
            doc_to_score[doc_key]["sources"].append("bm25")
        
        # Sort by RRF score
        sorted_results = sorted(
            doc_to_score.items(),
            key=lambda x: x[1]["score"],
            reverse=True
        )
        
        # Return top_k with merged metadata
        final = []
        for doc_key, data in sorted_results[:top_k]:
            result = data["result"].copy()
            result["rrf_score"] = round(data["score"], 6)
            result["sources"] = data["sources"]
            final.append(result)
        
        return final
    
    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Get embedding for text using OpenAI API
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector or None if failed
        """
        try:
            response = self.embedding_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get searcher statistics"""
        return {
            "documents_loaded": len(self.documents),
            "bm25_initialized": self.bm25 is not None,
            "pgvector_backend": "Supabase",
            "embedding_model": EMBEDDING_MODEL,
            "status": "ready" if self.pgvector_ready else "not_ready",
        }


# Global instance
searcher = HybridSearcher()


async def main():
    """CLI test"""
    await searcher.build_index()
    results = await searcher.search("limitation period section 73", top_k=5)
    for r in results:
        print(f"[{r.get('rrf_score', r.get('similarity', 0.0)):.4f}] {r['text'][:60]}...")


if __name__ == "__main__":
    asyncio.run(main())

