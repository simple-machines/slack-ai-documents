# src/api/app.py

from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
import vertexai
from vertexai.language_models import TextEmbeddingModel
import numpy as np

from ..storage import IndexStore
from ..indexer import DocumentProcessor
from ..config import PROJECT_ID, LOCATION, TOP_K

app = FastAPI(title="Vector Search Service")

# initialize services
index_store = IndexStore()
doc_processor = DocumentProcessor(PROJECT_ID, LOCATION)

class SearchQuery(BaseModel):
    query: str
    top_k: Optional[int] = TOP_K

class SearchResult(BaseModel):
    text: str
    score: float
    metadata: dict

@app.post("/search", response_model=List[SearchResult])
async def search(query: SearchQuery):
    try:
        # get query embedding
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        model = TextEmbeddingModel.from_pretrained("textembedding-gecko@003")
        query_emb = model.get_embeddings([query.query])[0].values
        query_emb = np.array([query_emb]).astype('float32')

        # search index
        D, I = index_store.search(query_emb, k=query.top_k)
        
        # format results
        results = []
        for distance, idx in zip(D[0], I[0]):
            chunk = index_store.metadata["chunks"][int(idx)]
            results.append(SearchResult(
                text=chunk["text"],
                score=float(distance),
                metadata=chunk["metadata"]
            ))
        
        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/documents/")
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

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
