from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.db.session import get_db
from app.api.v1.deps import get_current_user
from app.models.user import User, UserRole
from app.models.case import Case, CaseType, CaseStatus
from app.models.law import Law
from app.models.ruling import Ruling
from app.models.legal_article import LegalArticle
from app.models.subscription import Subscription, PlanType, SubscriptionStatus
from app.services.search_service import search_service
from app.services.rag_service import rag_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

async def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="صلاحية غير كافية")
    return current_user

# ─── Users ───

class AdminUserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: Optional[datetime] = None

class UpdateRoleRequest(BaseModel):
    role: str

class UpdateStatusRequest(BaseModel):
    is_active: bool

@router.get("/users", response_model=List[AdminUserResponse])
async def admin_list_users(skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(User).order_by(User.created_at.desc()).offset(skip).limit(limit))
    return [AdminUserResponse(id=u.id, email=u.email, full_name=u.full_name, role=u.role.value, is_active=u.is_active, is_verified=u.is_verified, created_at=u.created_at) for u in result.scalars().all()]

@router.put("/users/{user_id}/role")
async def admin_update_role(user_id: str, data: UpdateRoleRequest, db: AsyncSession = Depends(get_db), admin_user: User = Depends(require_admin)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    if data.role not in [e.value for e in UserRole]:
        raise HTTPException(status_code=400, detail="دور غير صالح")
    user.role = UserRole(data.role)
    await db.commit()
    logger.info("Admin changed user role", extra={"admin_id": admin_user.id, "target_user_id": user_id, "new_role": data.role})
    return {"status": "success", "detail": f"تم تغيير دور المستخدم إلى {data.role}"}

@router.put("/users/{user_id}/status")
async def admin_update_status(user_id: str, data: UpdateStatusRequest, db: AsyncSession = Depends(get_db), admin_user: User = Depends(require_admin)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    user.is_active = data.is_active
    await db.commit()
    logger.info("Admin updated user status", extra={"admin_id": admin_user.id, "target_user_id": user_id, "is_active": data.is_active})
    return {"status": "success", "detail": "تم تحديث حالة المستخدم"}

@router.delete("/users/{user_id}")
async def admin_delete_user(user_id: str, db: AsyncSession = Depends(get_db), admin_user: User = Depends(require_admin)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    await db.delete(user)
    await db.commit()
    logger.info("Admin deleted user", extra={"admin_id": admin_user.id, "deleted_user_id": user_id})
    return {"status": "success", "detail": "تم حذف المستخدم"}

# ─── Cases ───

class AdminCaseResponse(BaseModel):
    id: str
    title: str
    case_type: str
    status: str
    owner_name: Optional[str] = None
    owner_email: Optional[str] = None
    lawyer_name: Optional[str] = None
    created_at: Optional[datetime] = None

@router.get("/cases", response_model=List[AdminCaseResponse])
async def admin_list_cases(case_type: Optional[str] = None, status: Optional[str] = None, skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    query = select(Case)
    if case_type:
        query = query.where(Case.case_type == CaseType(case_type))
    if status:
        query = query.where(Case.status == CaseStatus(status))
    query = query.order_by(Case.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    cases = result.scalars().all()
    resp = []
    for c in cases:
        owner_name = owner_email = lawyer_name = None
        if c.owner:
            owner_name = c.owner.full_name
            owner_email = c.owner.email
        if c.lawyer:
            lawyer_name = c.lawyer.full_name
        resp.append(AdminCaseResponse(id=c.id, title=c.title, case_type=c.case_type.value, status=c.status.value, owner_name=owner_name, owner_email=owner_email, lawyer_name=lawyer_name, created_at=c.created_at))
    return resp

@router.delete("/cases/{case_id}")
async def admin_delete_case(case_id: str, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="القضية غير موجودة")
    await db.delete(case)
    await db.commit()
    return {"status": "success", "detail": "تم حذف القضية"}

# ─── Content (Laws + Rulings) ───

class AdminContentItem(BaseModel):
    id: str
    title: str
    type: str
    year: Optional[int] = None
    category: Optional[str] = None
    created_at: Optional[datetime] = None

class AdminContentResponse(BaseModel):
    items: List[AdminContentItem]
    total: int

@router.get("/content", response_model=AdminContentResponse)
async def admin_list_content(content_type: Optional[str] = Query(None, alias="type"), q: Optional[str] = None, skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    items = []
    total = 0
    if not content_type or content_type == "law":
        q_law = select(Law)
        if q:
            q_law = q_law.where(Law.title.ilike(f"%{q}%"))
        count_q = select(func.count()).select_from(q_law.subquery())
        total += (await db.execute(count_q)).scalar()
        result = await db.execute(q_law.order_by(Law.created_at.desc()).offset(skip).limit(limit))
        for law in result.scalars().all():
            items.append(AdminContentItem(id=law.id, title=law.title, type="law", year=law.year, category=law.category, created_at=law.created_at))
    if not content_type or content_type == "ruling":
        q_rul = select(Ruling)
        if q:
            q_rul = q_rul.where(Ruling.title.ilike(f"%{q}%"))
        count_q = select(func.count()).select_from(q_rul.subquery())
        total += (await db.execute(count_q)).scalar()
        result = await db.execute(q_rul.order_by(Ruling.created_at.desc()).offset(skip).limit(limit))
        for rul in result.scalars().all():
            year = rul.ruling_date.year if rul.ruling_date else None
            items.append(AdminContentItem(id=rul.id, title=rul.title, type="ruling", year=year, category=rul.case_type, created_at=rul.created_at))
    items.sort(key=lambda x: x.created_at or datetime.min, reverse=True)
    return AdminContentResponse(items=items[:limit], total=total)

class AddContentRequest(BaseModel):
    title: str
    type: str
    full_text: str
    year: Optional[int] = None
    category: Optional[str] = None

@router.post("/content")
async def admin_add_content(data: AddContentRequest, db: AsyncSession = Depends(get_db), admin_user: User = Depends(require_admin)):
    if data.type == "law":
        obj = Law(title=data.title, full_text=data.full_text, year=data.year, category=data.category)
    elif data.type == "ruling":
        obj = Ruling(title=data.title, full_text=data.full_text, case_type=data.category)
    else:
        raise HTTPException(status_code=400, detail="نوع غير صالح")
    db.add(obj)
    await db.commit()
    logger.info("Admin added content", extra={"admin_id": admin_user.id, "content_id": obj.id, "type": data.type, "title": data.title})
    return {"status": "success", "id": obj.id}

@router.delete("/content/{content_id}")
async def admin_delete_content(content_id: str, content_type: str = Query(alias="type"), db: AsyncSession = Depends(get_db), admin_user: User = Depends(require_admin)):
    model = Law if content_type == "law" else Ruling if content_type == "ruling" else None
    if not model:
        raise HTTPException(status_code=400, detail="نوع غير صالح")
    result = await db.execute(select(model).where(model.id == content_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="المحتوى غير موجود")
    await db.delete(obj)
    await db.commit()
    logger.info("Admin deleted content", extra={"admin_id": admin_user.id, "content_id": content_id, "type": content_type})
    return {"status": "success", "detail": "تم حذف المحتوى"}

# ─── Subscriptions ───

class AdminSubscriptionResponse(BaseModel):
    id: str
    user_id: str
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    plan: str
    status: str
    search_quota: int
    analysis_quota: int
    drafting_quota: int
    searches_used: int
    analyses_used: int
    drafts_used: int
    created_at: Optional[datetime] = None

class UpdateSubscriptionRequest(BaseModel):
    plan: Optional[str] = None
    search_quota: Optional[int] = None
    analysis_quota: Optional[int] = None
    drafting_quota: Optional[int] = None
    status: Optional[str] = None

@router.get("/subscriptions", response_model=List[AdminSubscriptionResponse])
async def admin_list_subscriptions(skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(Subscription).order_by(Subscription.created_at.desc()).offset(skip).limit(limit))
    subs = result.scalars().all()
    resp = []
    for s in subs:
        user_result = await db.execute(select(User).where(User.id == s.user_id))
        u = user_result.scalar_one_or_none()
        resp.append(AdminSubscriptionResponse(
            id=s.id, user_id=s.user_id, user_name=u.full_name if u else None, user_email=u.email if u else None,
            plan=s.plan.value, status=s.status.value, search_quota=s.search_quota, analysis_quota=s.analysis_quota,
            drafting_quota=s.drafting_quota, searches_used=s.searches_used, analyses_used=s.analyses_used,
            drafts_used=s.drafts_used, created_at=s.created_at
        ))
    return resp

@router.put("/subscriptions/{sub_id}")
async def admin_update_subscription(sub_id: str, data: UpdateSubscriptionRequest, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(Subscription).where(Subscription.id == sub_id))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="الاشتراك غير موجود")
    if data.plan is not None:
        sub.plan = PlanType(data.plan)
    if data.search_quota is not None:
        sub.search_quota = data.search_quota
    if data.analysis_quota is not None:
        sub.analysis_quota = data.analysis_quota
    if data.drafting_quota is not None:
        sub.drafting_quota = data.drafting_quota
    if data.status is not None:
        sub.status = SubscriptionStatus(data.status)
    await db.commit()
    return {"status": "success", "detail": "تم تحديث الاشتراك"}

# ─── RAG Status ───

@router.get("/rag/status")
async def admin_rag_status(_=Depends(require_admin)):
    try:
        collections = await rag_service.qdrant.get_collections()
        collection_info = None
        for c in collections.collections:
            if c.name == rag_service.collection_name:
                collection_info = {"name": c.name, "vectors_count": c.vectors_count}
        return {"status": "connected", "collection": collection_info}
    except Exception as e:
        return {"status": "disconnected", "error": str(e)}

@router.post("/rag/reindex")
async def admin_reindex_rag(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    try:
        await rag_service.qdrant.recreate_collection(
            collection_name=rag_service.collection_name,
            vectors_config=rag_service.qdrant.get_collection(rag_service.collection_name).vectors_config
        )
    except Exception:
        pass
    laws = (await db.execute(select(Law))).scalars().all()
    rulings = (await db.execute(select(Ruling))).scalars().all()
    articles = (await db.execute(select(LegalArticle).where(LegalArticle.is_active == True))).scalars().all()
    count = 0
    for law in laws:
        count += await rag_service.ingest_document(doc_id=law.id, title=law.title, content=law.full_text or "", metadata={"type": "law", "category": law.category})
    for ruling in rulings:
        count += await rag_service.ingest_document(doc_id=ruling.id, title=ruling.title, content=ruling.full_text or "", metadata={"type": "ruling", "court": ruling.court_name})
    for art in articles:
        law_result = await db.execute(select(Law.title).where(Law.id == art.law_id))
        law_title_row = law_result.first()
        law_title = law_title_row[0] if law_title_row else ""
        count += await rag_service.ingest_document(
            doc_id=f"art_{art.id}",
            title=f"{law_title} - مادة {art.article_number}",
            content=art.content,
            metadata={"type": "law_article", "law_id": art.law_id, "article_number": art.article_number}
        )
    return {"status": "success", "chunks_indexed": count}

# ─── Index ───

@router.post("/reindex-search")
async def admin_reindex_search(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    try:
        await search_service.rebuild_index(db)
        return {"status": "success", "detail": "تم إعادة بناء فهارس البحث"}
    except Exception as e:
        logger.error("Search reindex failed", exc_info=e)
        raise HTTPException(status_code=500, detail="فشل إعادة بناء فهارس البحث")
