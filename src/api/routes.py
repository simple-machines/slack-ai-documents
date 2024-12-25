# src/api/routes.py

from fastapi import APIRouter, HTTPException, File, UploadFile, Query
from pydantic import BaseModel, Field
from typing import List, Optional
import logging

from src.processor.gemini_processor import GeminiProcessor
from src.search.gemini_searcher import GeminiSearcher
from src.config import TOP_P_THRESHOLD, PROJECT_ID, LOCATION

router = APIRouter(tags=["API"])
logger = logging.getLogger(__name__)

# lazy initialization of processors
_doc_processor = None
_searcher = None

def get_doc_processor():
    global _doc_processor
    if _doc_processor is None:
        _doc_processor = GeminiProcessor()
    return _doc_processor

def get_searcher():
    global _searcher
    if _searcher is None:
        _searcher = GeminiSearcher()
    return _searcher

class SearchQuery(BaseModel):
    """schema for search query"""
    query: str = Field(..., description="the search query text")

class SearchResult(BaseModel):
    """schema for search result"""
    text: str = Field(..., description="The matched text content")
    score: float = Field(..., description="Relevance score")
    metadata: dict = Field(..., description="Additional metadata about the result")

@router.post("/find", response_model=List[SearchResult],
            summary="search documents",
            description="search through documents using Gemini based on relevance threshold")
async def find(query: SearchQuery):
    """
    search endpoint that returns relevant documents based on the query text and a relevance threshold.

    args:
        query (searchquery): the search query.

    returns:
        list[searchresult]: list of matching documents with scores.
    """
    try:
        logger.info(f"searching with query: {query.query}")
        searcher = get_searcher()
        results = await searcher.search(query.query)

        formatted_results = [
            SearchResult(
                text=result["text"],
                score=result["score"],
                metadata=result["metadata"]
            )
            for result in results
        ]

        logger.info(f"found {len(formatted_results)} results")
        return formatted_results

    except Exception as e:
        logger.error(f"search error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents",
            summary="upload document",
            description="upload and process a document using Gemini")
async def upload_document(
    file: UploadFile = File(..., description="the document file to upload")
):
    """
    upload and process a document.

    args:
        file (uploadfile): the document file to process

    returns:
        dict: success message with analysis
    """
    try:
        logger.info(f"processing document: {file.filename}")

        # save uploaded file temporarily
        temp_path = f"/tmp/{file.filename}"
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # process with Gemini
        processor = get_doc_processor()
        result = await processor.process_document(
            temp_path,
            metadata={"filename": file.filename}
        )

        logger.info(f"successfully processed document: {file.filename}")
        return {
            "message": "document processed successfully",
            "filename": file.filename,
            "analysis": result["analysis"]
        }

    except Exception as e:
        logger.error(f"document processing error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
