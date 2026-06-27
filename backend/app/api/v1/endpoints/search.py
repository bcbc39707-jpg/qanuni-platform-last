from fastapi import APIRouter, Query, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.search_service import search_service
from app.api.v1.deps import check_search_quota
from app.models.subscription import Subscription
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class SearchResult(BaseModel):
    id: str
    title: Optional[str] = None
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
    q: str = Query("", description="استعلام البحث"),
    doc_type: Optional[str] = Query(None, description="law, ruling, document"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
    category: Optional[str] = Query(None, description="constitution, law, regulation, decree"),
    division_id: Optional[str] = Query(None, description="مُعرف القسم القانوني"),
    year: Optional[int] = None,
    court: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    sub: Subscription = Depends(check_search_quota),
):
    try:
        filters = {}
        if year:
            filters["year"] = year
        if court:
            filters["court_name"] = court
        if category:
            filters["category"] = category
        if division_id:
            filters["division_id"] = division_id
        result = await search_service.search(db=db, query=q, doc_type=doc_type, page=page, size=size, filters=filters)
        sub_result = await db.execute(select(Subscription).where(Subscription.id == sub.id))
        tracked_sub = sub_result.scalar_one_or_none()
        if tracked_sub:
            tracked_sub.searches_used += 1
        await db.commit()
        return SearchResponse(
            query=q,
            total=result["total"],
            results=[SearchResult(**r) for r in result["results"]]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Search failed", exc_info=e)
        raise HTTPException(status_code=503, detail="خطأ في محرك البحث")

