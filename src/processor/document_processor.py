# src/indexer/document_processor.py

from typing import List, Dict
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import CHUNK_SIZE, CHUNK_OVERLAP
from src.indexer.embeddings import EmbeddingGenerator
from src.indexer.index_builder import IndexBuilder

class DocumentProcessor:
    def __init__(self, project_id: str, location: str):
        self.embedding_generator = EmbeddingGenerator(project_id, location)
        self.index_builder = IndexBuilder()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
        )

    def create_chunks(self, text: str, metadata: Dict = None) -> List[Dict]:
        """split document into chunks with metadata"""
        chunks = self.text_splitter.split_text(text)
        return [
            {
                "id": f"chunk_{i}",
                "text": chunk,
                "metadata": metadata or {}
            }
            for i, chunk in enumerate(chunks)
        ]

    def process_and_index_document(self, content: str, metadata: Dict = None) -> None:
        """process document and update index"""
        # create chunks
        chunks = self.create_chunks(content, metadata)
        
        # update index
        self.index_builder.update_index(chunks)
