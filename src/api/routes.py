# src/api/routes.py

from fastapi import APIRouter, HTTPException, File, UploadFile
from pydantic import BaseModel
from typing import List, Optional

from ..indexer import DocumentProcessor
from ..search.hybrid_searcher import HybridSearcher
from ..config import TOP_K, PROJECT_ID, LOCATION

router = APIRouter()
doc_processor = DocumentProcessor(PROJECT_ID, LOCATION)
searcher = HybridSearcher()

class SearchQuery(BaseModel):
    query: str
    top_k: Optional[int] = TOP_K

class SearchResult(BaseModel):
    text: str
    score: float
    metadata: dict

@router.post("/search", response_model=List[SearchResult])
async def search(query: SearchQuery):
    try:
        results = searcher.search(query.query, query.top_k)
        return [
            SearchResult(
                text=result["text"],
                score=result["score"],
                metadata=result["metadata"]
            )
            for result in results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents/")
async def upload_document(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        doc_processor.process_and_index_document(
            content=contents.decode(),
            metadata={"filename": file.filename}
        )
        return {"message": "document processed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))