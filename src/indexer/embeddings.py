# src/indexer/embeddings.py

import vertexai
from vertexai.language_models import TextEmbeddingModel
from typing import List
import time
from tqdm import tqdm

class EmbeddingGenerator:
    def __init__(self, project_id: str, location: str):
        vertexai.init(project=project_id, location=location)
        self.model = TextEmbeddingModel.from_pretrained("textembedding-gecko@003")

    def get_embeddings(self, texts: List[str], batch_size: int = 5) -> List[List[float]]:
        """Generate embeddings for a list of texts using batching"""
        embeddings = []
        for i in tqdm(range(0, len(texts), batch_size)):
            batch = texts[i:i + batch_size]
            # Add delay to respect rate limits
            time.sleep(1)  
            results = self.model.get_embeddings(batch)
            embeddings.extend([emb.values for emb in results])
        return embeddings
