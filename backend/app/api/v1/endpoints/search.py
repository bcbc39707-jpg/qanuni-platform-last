from fastapi import APIRouter, Query, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.services.search_service import search_service

router = APIRouter()

class SearchResult(BaseModel):
    id: str
    title: str
    snippet: str
    doc_type: str
    score: float
    source: Optional[str] = None

class SearchResponse(BaseModel):
    query: str
    total: int
    results: List[SearchResult]

@router.get("/", response_model=SearchResponse)
async def search_legal(
    q: str = Query(..., min_length=2, description="??????? ?????"),
    doc_type: Optional[str] = Query(None, description="law, ruling, document"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
    year: Optional[int] = None,
    court: Optional[str] = None,
):
    try:
        filters = {}
        if year:
            filters["year"] = year
        if court:
            filters["court_name"] = court
        result = await search_service.search(query=q, doc_type=doc_type, page=page, size=size, filters=filters)
        return SearchResponse(
            query=q,
            total=result["total"],
            results=[SearchResult(**r) for r in result["results"]]
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"??? ?? ???? ?????: {str(e)}")

@router.post("/index-init")
async def initialize_search_indices():
    try:
        await search_service.create_indices()
        return {"status": "success", "message": "?? ????? ????? ????? ?????"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
