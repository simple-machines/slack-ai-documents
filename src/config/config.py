# src/config/config.py

import os
from pathlib import Path

# project configuration
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION", "us-central1")  
BUCKET_NAME = os.getenv("BUCKET_NAME")

# vertex ai configuration 
EMBEDDING_MODEL = "textembedding-gecko@003"
GEMINI_MODEL = "gemini-1.0-pro-001"

# faiss configuration
INDEX_BLOB_PATH = "indexes/faiss_index.bin"
METADATA_BLOB_PATH = "indexes/metadata.json"

# document processing
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# search configuration  
TOP_K = 5
SEMANTIC_WEIGHT = 0.7  # weight for semantic search vs keyword