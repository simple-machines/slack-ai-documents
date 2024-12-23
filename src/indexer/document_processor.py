# src/indexer/document_processor.py

from typing import List, Dict
import json
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.config import CHUNK_SIZE, CHUNK_OVERLAP

def create_chunks(content: str, metadata: Dict = None) -> List[Dict]:
    """split document into chunks with metadata"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
    )
    
    texts = splitter.split_text(content)
    chunks = []
    
    for i, text in enumerate(texts):
        chunk = {
            "id": f"chunk_{i}",
            "text": text,
            "metadata": metadata or {}
        }
        chunks.append(chunk)
    
    return chunks
