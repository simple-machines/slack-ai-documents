# src/indexer/index_builder.py

import faiss
import numpy as np
from typing import List, Dict

from src.storage import IndexStore
from src.indexer.embeddings import EmbeddingGenerator
from src.config import PROJECT_ID, LOCATION

class IndexBuilder:
    def __init__(self):
        self.index_store = IndexStore()
        self.embedding_generator = EmbeddingGenerator(PROJECT_ID, LOCATION)

    def create_index(self, chunks: List[Dict]) -> None:
        """create new FAISS index from chunks"""
        # generate embeddings
        texts = [chunk["text"] for chunk in chunks]
        embeddings = self.embedding_generator.get_embeddings(texts)
        embeddings_array = np.array(embeddings).astype('float32')

        # create FAISS index
        dimension = len(embeddings[0])
        index = faiss.IndexFlatIP(dimension)
        index.add(embeddings_array)

        # save index and metadata
        metadata = {
            "chunks": chunks,
            "dimension": dimension
        }
        self.index_store.save(index, metadata)

    def update_index(self, new_chunks: List[Dict]) -> None:
        """update existing index with new chunks"""
        # Generate embeddings for new chunks
        texts = [chunk["text"] for chunk in new_chunks]
        new_embeddings = self.embedding_generator.get_embeddings(texts)
        new_embeddings_array = np.array(new_embeddings).astype('float32')

        # if index exists, append to it
        if self.index_store.exists():
            index = self.index_store.index
            metadata = self.index_store.metadata
            
            # add new embeddings to index
            index.add(new_embeddings_array)
            
            # update metadata
            metadata["chunks"].extend(new_chunks)
            
            self.index_store.save(index, metadata)
        else:
            # create new index
            self.create_index(new_chunks)
