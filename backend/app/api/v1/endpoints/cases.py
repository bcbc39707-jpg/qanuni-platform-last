from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
from app.db.session import get_db
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.models.case import Case, CaseStatus, CaseType

router = APIRouter()

class CaseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    case_number: Optional[str] = None
    case_type: CaseType
    court_name: Optional[str] = None

class CaseResponse(BaseModel):
    id: str
    title: str
    case_type: str
    status: str

@router.post("/", response_model=CaseResponse)
async def create_case(data: CaseCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    case = Case(title=data.title, description=data.description, case_number=data.case_number, case_type=data.case_type, court_name=data.court_name, owner_id=current_user.id)
    db.add(case)
    await db.commit()
    await db.refresh(case)
    return CaseResponse(id=case.id, title=case.title, case_type=case.case_type.value, status=case.status.value)

@router.get("/", response_model=List[CaseResponse])
async def list_cases(skip: int = 0, limit: int = 20, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Case).where(Case.owner_id == current_user.id).offset(skip).limit(limit))
    return [CaseResponse(id=c.id, title=c.title, case_type=c.case_type.value, status=c.status.value) for c in result.scalars().all()]
