# src/api/routes.py

from fastapi import APIRouter, HTTPException, File, UploadFile, Query
from pydantic import BaseModel, Field
from typing import List, Optional
import logging

from src.indexer import DocumentProcessor
from src.search.hybrid_searcher import HybridSearcher
from src.config import TOP_K, PROJECT_ID, LOCATION

router = APIRouter(tags=["API"])
logger = logging.getLogger(__name__)

doc_processor = DocumentProcessor(PROJECT_ID, LOCATION)
searcher = HybridSearcher()

class SearchQuery(BaseModel):
    """Schema for search query"""
    query: str = Field(..., description="The search query text")
    top_k: Optional[int] = Field(default=TOP_K, description="Number of results to return")

class SearchResult(BaseModel):
    """Schema for search result"""
    text: str = Field(..., description="The matched text content")
    score: float = Field(..., description="Relevance score")
    metadata: dict = Field(..., description="Additional metadata about the result")

@router.post("/find", response_model=List[SearchResult], 
            summary="Search documents",
            description="Search through indexed documents using a text query")
async def find(query: SearchQuery):
    """
    Search endpoint that returns relevant documents based on the query text.
    
    Args:
        query (SearchQuery): The search query and options
        
    Returns:
        List[SearchResult]: List of matching documents with scores
    """
    try:
        logger.info(f"Searching with query: {query.query}")
        results = searcher.search(query.query, query.top_k)
        
        formatted_results = [
            SearchResult(
                text=result["text"],
                score=result["score"],
                metadata=result["metadata"]
            )
            for result in results
        ]
        
        logger.info(f"Found {len(formatted_results)} results")
        return formatted_results
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents",
            summary="Upload document",
            description="Upload a document to be indexed for searching")
async def upload_document(
    file: UploadFile = File(..., description="The document file to upload")
):
    """
    Upload and process a document for indexing.
    
    Args:
        file (UploadFile): The document file to process
        
    Returns:
        dict: Success message
    """
    try:
        logger.info(f"Processing document: {file.filename}")
        contents = await file.read()
        
        doc_processor.process_and_index_document(
            content=contents.decode(),
            metadata={"filename": file.filename}
        )
        
        logger.info(f"Successfully processed document: {file.filename}")
        return {
            "message": "Document processed successfully",
            "filename": file.filename
        }
        
    except Exception as e:
        logger.error(f"Document processing error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
