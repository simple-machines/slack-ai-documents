# src/indexer/index_builder.py

import faiss
import numpy as np
from typing import List, Dict
import json
from src.storage.gcs import GCSStorage
from src.indexer.embeddings import EmbeddingGenerator
from src.config import PROJECT_ID, LOCATION, INDEX_BLOB_PATH, METADATA_BLOB_PATH

class IndexBuilder:
    def __init__(self):
        self.embedding_generator = EmbeddingGenerator(PROJECT_ID, LOCATION)
        self.storage = GCSStorage()
        
    def build_index(self, chunks: List[Dict]) -> None:
        """build FAISS index from document chunks"""
        # generate embeddings
        texts = [chunk["text"] for chunk in chunks]
        embeddings = self.embedding_generator.get_embeddings(texts)
        
        # build FAISS index
        dimension = len(embeddings[0])
        index = faiss.IndexFlatIP(dimension)  # inner product for cosine similarity
        embeddings_array = np.array(embeddings).astype('float32')
        index.add(embeddings_array)
        
        # save metadata mapping
        metadata = {
            "chunks": chunks,
            "dimension": dimension
        }
        
        # save to GCS
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            faiss.write_index(index, temp_file.name)
            self.storage.upload_file(temp_file.name, INDEX_BLOB_PATH)
            
        self.storage.upload_from_string(
            json.dumps(metadata),
            METADATA_BLOB_PATH
        )
