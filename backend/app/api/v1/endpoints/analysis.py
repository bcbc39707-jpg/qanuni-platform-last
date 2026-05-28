from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.services.rag_service import rag_service

router = APIRouter()

class AnalysisRequest(BaseModel):
    text: str
    analysis_type: str = "general"

class QueryRequest(BaseModel):
    question: str
    top_k: int = 5

class DraftRequest(BaseModel):
    doc_type: str  # claim, defense, memo, contract, appeal
    context: str
    instructions: str = ""

class QueryResponse(BaseModel):
    answer: str
    sources: List[dict]
    chunks_used: int

@router.post("/analyze")
async def analyze_legal_text(data: AnalysisRequest, current_user: User = Depends(get_current_user)):
    try:
        result = await rag_service.analyze_case(data.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"??? ?? ???????: {str(e)}")

@router.post("/query", response_model=QueryResponse)
async def query_legal(data: QueryRequest, current_user: User = Depends(get_current_user)):
    try:
        result = await rag_service.query(data.question, top_k=data.top_k)
        return QueryResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"??? ?? ?????????: {str(e)}")

@router.post("/draft")
async def draft_document(data: DraftRequest, current_user: User = Depends(get_current_user)):
    try:
        result = await rag_service.draft_legal_document(data.doc_type, data.context, data.instructions)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"??? ?? ???????: {str(e)}")

@router.post("/ingest")
async def ingest_document(doc_id: str, title: str, content: str, metadata: dict = None, current_user: User = Depends(get_current_user)):
    if current_user.role.value not in ["admin", "reviewer"]:
        raise HTTPException(status_code=403, detail="?????? ??? ?????")
    try:
        chunks_count = await rag_service.ingest_document(doc_id, title, content, metadata)
        return {"status": "success", "chunks_indexed": chunks_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
