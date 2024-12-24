# src/storage/index_store.py

import json
import faiss
import numpy as np
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple

from src.config import BUCKET_NAME, INDEX_BLOB_PATH, METADATA_BLOB_PATH
from src.storage.gcs import GCSHandler

class IndexStore:
    def __init__(self):
        """initialize index store with GCS handler"""
        self.gcs = GCSHandler(BUCKET_NAME)
        self._index: Optional[faiss.Index] = None
        self._metadata: Optional[Dict] = None

    @property
    def index(self) -> faiss.Index:
        """lazy load FAISS index"""
        if self._index is None:
            self._load_index()
        return self._index

    @property
    def metadata(self) -> Dict:
        """lazy load metadata"""
        if self._metadata is None:
            self._load_metadata()
        return self._metadata

    def _load_index(self) -> None:
        """load FAISS index from GCS"""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            self.gcs.download_file(INDEX_BLOB_PATH, temp_file.name)
            self._index = faiss.read_index(temp_file.name)
        Path(temp_file.name).unlink()

    def _load_metadata(self) -> None:
        """load metadata from GCS"""
        self._metadata = self.gcs.download_json(METADATA_BLOB_PATH)

    def save(self, index: faiss.Index, metadata: Dict) -> None:
        """save both index and metadata to GCS"""
        # save FAISS index
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            faiss.write_index(index, temp_file.name)
            self.gcs.upload_file(temp_file.name, INDEX_BLOB_PATH)
        Path(temp_file.name).unlink()

        # save metadata
        self.gcs.upload_json(metadata, METADATA_BLOB_PATH)

        # update local cache
        self._index = index
        self._metadata = metadata

    def search(self, query_embedding: np.ndarray, k: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        """search the index for similar vectors
        
        args:
            query_embedding: query vector of shape (1, dim)
            k: number of results to return
            
        returns:
            tuple of (distances, indices)
        """
        return self.index.search(query_embedding, k)

    def exists(self) -> bool:
        """check if index and metadata exist in GCS"""
        return (
            self.gcs.file_exists(INDEX_BLOB_PATH) and 
            self.gcs.file_exists(METADATA_BLOB_PATH)
        )

    def clear_cache(self) -> None:
        """clear the local index and metadata cache"""
        self._index = None 
        self._metadata = None
