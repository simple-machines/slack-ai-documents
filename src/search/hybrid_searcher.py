# src/search/hybrid_searcher.py

from typing import List, Dict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from ..storage import IndexStore
from ..indexer.embeddings import EmbeddingGenerator
from ..config import PROJECT_ID, LOCATION, HYBRID_ALPHA

class HybridSearcher:
    def __init__(self):
        self.index_store = IndexStore()
        self.embedding_generator = EmbeddingGenerator(PROJECT_ID, LOCATION)
        self._tfidf = None
        self._tfidf_matrix = None
        
    def _initialize_tfidf(self):
        """initialize TF-IDF for keyword search"""
        if self._tfidf is None:
            texts = [chunk["text"] for chunk in self.index_store.metadata["chunks"]]
            self._tfidf = TfidfVectorizer()
            self._tfidf_matrix = self._tfidf.fit_transform(texts)
    
    def _semantic_search(self, query: str, k: int) -> List[Dict]:
        """perform semantic search using FAISS"""
        # generate query embedding
        query_embedding = self.embedding_generator.get_embeddings([query])[0]
        query_embedding = np.array([query_embedding]).astype('float32')
        
        # search FAISS index
        D, I = self.index_store.search(query_embedding, k)
        
        return [{
            "index": idx,
            "score": score,
            "chunk": self.index_store.metadata["chunks"][idx]
        } for score, idx in zip(D[0], I[0])]
    
    def _keyword_search(self, query: str, k: int) -> List[Dict]:
        """perform keyword search using TF-IDF"""
        self._initialize_tfidf()
        
        # transform query and calculate similarities
        query_vector = self._tfidf.transform([query])
        similarities = (self._tfidf_matrix @ query_vector.T).toarray().flatten()
        
        # get top k results
        top_k_idx = np.argsort(similarities)[-k:][::-1]
        
        return [{
            "index": idx,
            "score": similarities[idx],
            "chunk": self.index_store.metadata["chunks"][idx]
        } for idx in top_k_idx]

    def search(self, query: str, k: int = 5) -> List[Dict]:
        """perform hybrid search combining semantic and keyword search"""
        # get results from both methods
        semantic_results = self._semantic_search(query, k)
        keyword_results = self._keyword_search(query, k)
        
        # combine and normalize scores
        all_results = {}
        
        # add semantic results
        for res in semantic_results:
            all_results[res["index"]] = {
                "text": res["chunk"]["text"],
                "metadata": res["chunk"]["metadata"],
                "score": HYBRID_ALPHA * res["score"],
                "found_by": ["semantic"]
            }
            
        # add or update with keyword results
        for res in keyword_results:
            if res["index"] in all_results:
                all_results[res["index"]]["score"] += (1 - HYBRID_ALPHA) * res["score"]
                all_results[res["index"]]["found_by"].append("keyword")
            else:
                all_results[res["index"]] = {
                    "text": res["chunk"]["text"],
                    "metadata": res["chunk"]["metadata"],
                    "score": (1 - HYBRID_ALPHA) * res["score"],
                    "found_by": ["keyword"]
                }
        
        # sort by combined score and return top k
        sorted_results = sorted(
            all_results.values(), 
            key=lambda x: x["score"], 
            reverse=True
        )[:k]
        
        return sorted_results
