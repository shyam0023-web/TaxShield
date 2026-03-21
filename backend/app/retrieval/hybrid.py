"""
TaxShield — Hybrid Search (BM25 + FAISS + Cohere Rerank)
Pipeline: BM25 (keyword) + FAISS (semantic) → RRF fusion → Cohere Rerank → top_k
Lazy-loads SentenceTransformer and Cohere client to avoid startup overhead.
"""
import os
import numpy as np
import re
import logging
from typing import List, Dict, Optional
import faiss
from rank_bm25 import BM25Okapi
from app.retrieval.ingestion import load_circulars, LegalDocument

logger = logging.getLogger(__name__)

# Search defaults
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
FAISS_K = 15   # Pull more candidates for reranking
BM25_K = 15
RERANK_CANDIDATES = 20  # Send this many to Cohere for reranking


def simple_tokenize(text: str) -> List[str]:
    return re.findall(r"\w+", text.lower())


class HybridSearcher:
    def __init__(self):
        self.documents: List[LegalDocument] = []
        self.bm25 = None
        self._encoder = None
        self.index = None
        self._cohere_client = None
        self._cohere_available: Optional[bool] = None  # None = not checked yet

    @property
    def encoder(self):
        """Lazy-load SentenceTransformer only when first needed."""
        if self._encoder is None:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
            self._encoder = SentenceTransformer(EMBEDDING_MODEL)
            logger.info("Embedding model loaded successfully")
        return self._encoder

    @property
    def cohere(self):
        """Lazy-load Cohere client. Returns None if not available."""
        if self._cohere_available is None:
            try:
                import cohere
                api_key = os.environ.get("COHERE_API_KEY", "")
                if not api_key:
                    logger.warning("COHERE_API_KEY not set — reranking disabled. "
                                   "Get a free key at https://dashboard.cohere.com/api-keys")
                    self._cohere_available = False
                    return None

                self._cohere_client = cohere.ClientV2(api_key=api_key)
                self._cohere_available = True
                logger.info("Cohere reranker initialized")
            except ImportError:
                logger.warning("cohere package not installed — reranking disabled. "
                               "Install with: pip install cohere")
                self._cohere_available = False
        return self._cohere_client if self._cohere_available else None

    def build_index(self):
        self.documents = load_circulars()
        if not self.documents:
            logger.warning("No documents to index!")
            return

        tokenized_corpus = [simple_tokenize(doc.text) for doc in self.documents]
        self.bm25 = BM25Okapi(tokenized_corpus)

        texts = [doc.text for doc in self.documents]
        embeddings = self.encoder.encode(texts, normalize_embeddings=True)

        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(np.array(embeddings).astype('float32'))

        logger.info(f"Indices built with {len(self.documents)} documents, dim={dimension}")

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Hybrid search with optional Cohere reranking.
        Pipeline: BM25 + FAISS → RRF fusion → Cohere Rerank (if available) → top_k
        """
        if not self.documents:
            return []

        # ═══ Stage 1: FAISS semantic search ═══
        query_vector = self.encoder.encode([query], normalize_embeddings=True)
        distances, faiss_indices = self.index.search(
            np.array(query_vector).astype('float32'),
            min(FAISS_K, len(self.documents))
        )

        faiss_results = {}
        for rank, idx in enumerate(faiss_indices[0]):
            if idx != -1:
                faiss_results[idx] = rank

        # ═══ Stage 2: BM25 keyword search ═══
        tokenized_query = simple_tokenize(query)
        bm25_scores = self.bm25.get_scores(tokenized_query)
        top_bm25_indices = np.argsort(bm25_scores)[-BM25_K:][::-1]

        bm25_results = {}
        for rank, idx in enumerate(top_bm25_indices):
            if bm25_scores[idx] > 0:
                bm25_results[idx] = rank

        # ═══ Stage 3: RRF fusion ═══
        RRF_K = 60
        final_scores = {}
        all_indices = set(faiss_results.keys()) | set(bm25_results.keys())

        for idx in all_indices:
            score = 0
            if idx in faiss_results:
                score += 1 / (RRF_K + faiss_results[idx])
            if idx in bm25_results:
                score += 1 / (RRF_K + bm25_results[idx])
            final_scores[idx] = score

        # Get top candidates for reranking (more than top_k)
        sorted_indices = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
        candidates_count = min(RERANK_CANDIDATES, len(sorted_indices))
        candidate_pairs = sorted_indices[:candidates_count]

        # ═══ Stage 4: Cohere Rerank (if available) ═══
        if self.cohere and len(candidate_pairs) > 1:
            try:
                results = self._rerank_with_cohere(query, candidate_pairs, top_k)
                logger.info(f"Reranked {len(candidate_pairs)} candidates → {len(results)} results")
                return results
            except Exception as e:
                logger.warning(f"Cohere rerank failed ({e}), using RRF scores only")

        # Fallback: return RRF-scored results without reranking
        results = []
        for idx, score in candidate_pairs[:top_k]:
            doc = self.documents[idx]
            results.append({
                "doc_id": doc.doc_id,
                "text": doc.text,
                "score": score,
                "metadata": doc.metadata,
                "reranked": False,
            })

        return results

    def _rerank_with_cohere(self, query: str, candidate_pairs: List, top_k: int) -> List[Dict]:
        """
        Rerank candidates using Cohere Rerank API.
        Sends document texts to Cohere, gets relevance scores, returns top_k.
        """
        # Prepare documents for Cohere
        candidate_docs = []
        candidate_indices = []
        for idx, rrf_score in candidate_pairs:
            doc = self.documents[idx]
            # Cohere accepts strings — send first 1000 chars to stay within limits
            candidate_docs.append(doc.text[:1000])
            candidate_indices.append(idx)

        # Call Cohere Rerank
        response = self.cohere.rerank(
            model="rerank-v3.5",
            query=query,
            documents=candidate_docs,
            top_n=min(top_k, len(candidate_docs)),
        )

        # Build results from reranked order
        results = []
        for item in response.results:
            original_idx = candidate_indices[item.index]
            doc = self.documents[original_idx]
            results.append({
                "doc_id": doc.doc_id,
                "text": doc.text,
                "score": item.relevance_score,
                "metadata": doc.metadata,
                "reranked": True,
            })

        return results


searcher = HybridSearcher()

if __name__ == "__main__":
    searcher.build_index()
    results = searcher.search("limitation period section 73")
    for r in results:
        reranked = "✓" if r.get("reranked") else "✗"
        print(f"[{r['score']:.4f}] [{reranked}] {r['doc_id']} - {r['text'][:50]}...")
