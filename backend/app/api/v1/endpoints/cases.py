from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
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

class CaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    case_number: Optional[str] = None
    case_type: Optional[CaseType] = None
    status: Optional[CaseStatus] = None
    court_name: Optional[str] = None

class CaseDocument(BaseModel):
    id: str
    title: str
    doc_type: str
    file_size: Optional[int] = None
    created_at: Optional[datetime] = None

class CaseDetail(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    case_number: Optional[str] = None
    case_type: str
    status: str
    court_name: Optional[str] = None
    owner_id: str
    lawyer_id: Optional[str] = None
    created_at: Optional[datetime] = None
    documents: List[CaseDocument] = []

class CaseListItem(BaseModel):
    id: str
    title: str
    case_type: str
    status: str
    created_at: Optional[datetime] = None

@router.post("/", response_model=CaseDetail)
async def create_case(data: CaseCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    case = Case(title=data.title, description=data.description, case_number=data.case_number, case_type=data.case_type, court_name=data.court_name, owner_id=current_user.id)
    db.add(case)
    await db.commit()
    await db.refresh(case)
    return CaseDetail(id=case.id, title=case.title, description=case.description, case_number=case.case_number, case_type=case.case_type.value, status=case.status.value, court_name=case.court_name, owner_id=case.owner_id, lawyer_id=case.lawyer_id, created_at=case.created_at, documents=[])

@router.get("/", response_model=List[CaseListItem])
async def list_cases(skip: int = 0, limit: int = 20, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Case).where(Case.owner_id == current_user.id).order_by(Case.created_at.desc()).offset(skip).limit(limit))
    return [CaseListItem(id=c.id, title=c.title, case_type=c.case_type.value, status=c.status.value, created_at=c.created_at) for c in result.scalars().all()]

@router.get("/{case_id}", response_model=CaseDetail)
async def get_case(case_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="القضية غير موجودة")
    if case.owner_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="لا تملك صلاحية الوصول لهذه القضية")
    docs = [CaseDocument(id=d.id, title=d.title, doc_type=d.doc_type.value, file_size=d.file_size, created_at=d.created_at) for d in case.documents]
    return CaseDetail(id=case.id, title=case.title, description=case.description, case_number=case.case_number, case_type=case.case_type.value, status=case.status.value, court_name=case.court_name, owner_id=case.owner_id, lawyer_id=case.lawyer_id, created_at=case.created_at, documents=docs)

@router.put("/{case_id}", response_model=CaseDetail)
async def update_case(case_id: str, data: CaseUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="القضية غير موجودة")
    if case.owner_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="لا تملك صلاحية تعديل هذه القضية")
    if data.title is not None:
        case.title = data.title
    if data.description is not None:
        case.description = data.description
    if data.case_number is not None:
        case.case_number = data.case_number
    if data.case_type is not None:
        case.case_type = data.case_type
    if data.status is not None:
        case.status = data.status
    if data.court_name is not None:
        case.court_name = data.court_name
    await db.commit()
    await db.refresh(case)
    docs = [CaseDocument(id=d.id, title=d.title, doc_type=d.doc_type.value, file_size=d.file_size, created_at=d.created_at) for d in case.documents]
    return CaseDetail(id=case.id, title=case.title, description=case.description, case_number=case.case_number, case_type=case.case_type.value, status=case.status.value, court_name=case.court_name, owner_id=case.owner_id, lawyer_id=case.lawyer_id, created_at=case.created_at, documents=docs)

@router.delete("/{case_id}")
async def delete_case(case_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="القضية غير موجودة")
    if case.owner_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="لا تملك صلاحية حذف هذه القضية")
    await db.delete(case)
    await db.commit()
    return {"status": "success", "detail": "تم حذف القضية بنجاح"}

@router.post("/{case_id}/assign")
async def assign_case(case_id: str, lawyer_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role.value not in ["admin", "reviewer"]:
        raise HTTPException(status_code=403, detail="صلاحية غير كافية لتعيين محامٍ")
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="القضية غير موجودة")
    lawyer_result = await db.execute(select(User).where(User.id == lawyer_id))
    lawyer = lawyer_result.scalar_one_or_none()
    if not lawyer or lawyer.role.value != "lawyer":
        raise HTTPException(status_code=400, detail="المستخدم المحدد ليس محامياً")
    case.lawyer_id = lawyer_id
    case.status = CaseStatus.IN_PROGRESS
    await db.commit()
    return {"status": "success", "detail": "تم تعيين المحامي للقضية"}
