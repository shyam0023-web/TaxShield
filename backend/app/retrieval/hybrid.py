import numpy as np
import re
from typing import List, Dict
import faiss
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
from app.retrieval.ingestion import load_circulars, LegalDocument
from app.config import EMBEDDING_MODEL, FAISS_K, BM25_K

def simple_tokenize(text: str) -> List[str]:
    return re.findall(r"\w+", text.lower())

class HybridSearcher:
    def __init__(self):
        self.documents: List[LegalDocument] = []
        self.bm25 = None
        self.encoder = SentenceTransformer(EMBEDDING_MODEL)
        self.index = None

    def build_index(self):
        self.documents = load_circulars()
        if not self.documents:
            print("No documents to index!")
            return
        
        tokenized_corpus = [simple_tokenize(doc.text) for doc in self.documents]
        self.bm25 = BM25Okapi(tokenized_corpus)
        
        texts = [doc.text for doc in self.documents]
        embeddings = self.encoder.encode(texts, normalize_embeddings=True)
        
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(np.array(embeddings).astype('float32'))
        
        print(f"✅ Indices built with {len(self.documents)} documents, dim={dimension}")

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        if not self.documents:
            return []
        
        query_vector = self.encoder.encode([query], normalize_embeddings=True)
        distances, faiss_indices = self.index.search(
            np.array(query_vector).astype('float32'), 
            min(FAISS_K, len(self.documents))
        )
        
        faiss_results = {}
        for rank, idx in enumerate(faiss_indices[0]):
            if idx != -1:
                faiss_results[idx] = rank
        
        tokenized_query = simple_tokenize(query)
        bm25_scores = self.bm25.get_scores(tokenized_query)
        top_bm25_indices = np.argsort(bm25_scores)[-BM25_K:][::-1]
        
        bm25_results = {}
        for rank, idx in enumerate(top_bm25_indices):
            if bm25_scores[idx] > 0:
                bm25_results[idx] = rank
        
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
        
        results = []
        sorted_indices = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
        
        for idx, score in sorted_indices[:top_k]:
            doc = self.documents[idx]
            results.append({
                "doc_id": doc.doc_id,
                "text": doc.text,
                "score": score,
                "metadata": doc.metadata
            })
            
        return results

searcher = HybridSearcher()

if __name__ == "__main__":
    searcher.build_index()
    results = searcher.search("limitation period section 73")
    for r in results:
        print(f"[{r['score']:.4f}] {r['doc_id']} - {r['text'][:50]}...")
