# src/config/config.py

import os

# Google Cloud settings
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION", "us-central1")
BUCKET_NAME = os.getenv("BUCKET_NAME")

# Vertex AI models
EMBEDDING_MODEL = "textembedding-gecko@003"
GEMINI_MODEL = "gemini-1.0-pro-001"

# storage paths
INDEX_BLOB_PATH = "indexes/faiss_index.bin"
METADATA_BLOB_PATH = "indexes/metadata.json"
DOCUMENTS_PREFIX = "documents/"

# document processing
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# search settings
TOP_K = 5
HYBRID_ALPHA = 0.7  # weight for semantic vs keyword search

# API settings
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10MB in bytes