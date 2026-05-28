from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

class SearchResult(BaseModel):
    id: str
    title: str
    snippet: str
    doc_type: str
    score: float

class SearchResponse(BaseModel):
    query: str
    total: int
    results: List[SearchResult]

@router.get("/", response_model=SearchResponse)
async def search_legal(q: str = Query(..., min_length=2), doc_type: Optional[str] = None, page: int = 1, size: int = 10):
    # TODO: Implement Elasticsearch search
    return SearchResponse(query=q, total=0, results=[])
