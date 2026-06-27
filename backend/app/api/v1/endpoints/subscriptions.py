from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.db.session import get_db
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.models.subscription import Subscription, PlanType, SubscriptionStatus

router = APIRouter()

class SubscriptionResponse(BaseModel):
    plan: str
    status: str
    search_quota: int
    analysis_quota: int
    drafting_quota: int
    advanced_ocr_quota: int
    searches_used: int
    analyses_used: int
    drafts_used: int
    advanced_ocr_used: int

class UsageResponse(BaseModel):
    searches_left: int
    analyses_left: int
    drafts_left: int
    advanced_ocr_left: int
    searches_quota: int
    analyses_quota: int
    drafts_quota: int
    advanced_ocr_quota: int

@router.get("/usage", response_model=UsageResponse)
async def get_usage(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Subscription).where(Subscription.user_id == current_user.id))
    sub = result.scalar_one_or_none()
    if not sub:
        sub = Subscription(user_id=current_user.id, plan=PlanType.FREE, search_quota=10, analysis_quota=0, drafting_quota=0)
        db.add(sub)
        await db.commit()
        await db.refresh(sub)
    return UsageResponse(
        searches_left=max(0, sub.search_quota - sub.searches_used),
        analyses_left=max(0, sub.analysis_quota - sub.analyses_used),
        drafts_left=max(0, sub.drafting_quota - sub.drafts_used),
        advanced_ocr_left=max(0, sub.advanced_ocr_quota - sub.advanced_ocr_used),
        searches_quota=sub.search_quota,
        analyses_quota=sub.analysis_quota,
        drafts_quota=sub.drafting_quota,
        advanced_ocr_quota=sub.advanced_ocr_quota,
    )

@router.get("/me", response_model=SubscriptionResponse)
async def get_my_subscription(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Subscription).where(Subscription.user_id == current_user.id))
    sub = result.scalar_one_or_none()
    if not sub:
        sub = Subscription(user_id=current_user.id, plan=PlanType.FREE, search_quota=10, analysis_quota=0, drafting_quota=0)
        db.add(sub)
        await db.commit()
        await db.refresh(sub)
    return SubscriptionResponse(
        plan=sub.plan.value, status=sub.status.value,
        search_quota=sub.search_quota, analysis_quota=sub.analysis_quota,
        drafting_quota=sub.drafting_quota, advanced_ocr_quota=sub.advanced_ocr_quota,
        searches_used=sub.searches_used, analyses_used=sub.analyses_used,
        drafts_used=sub.drafts_used, advanced_ocr_used=sub.advanced_ocr_used,
    )

@router.post("/upgrade")
async def upgrade_plan(plan: str, payment_token: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    quotas = {
        "professional": {"search": 9999, "analysis": 50, "drafting": 20, "advanced_ocr": 30, "price_usd": 23},
        "enterprise": {"search": 9999, "analysis": 9999, "drafting": 9999, "advanced_ocr": 500, "price_usd": 63},
    }
    if plan not in quotas:
        raise HTTPException(status_code=400, detail="خطة غير صالحة")
    if not payment_token or len(payment_token) < 8:
        raise HTTPException(status_code=402, detail="الدفع مطلوب للترقية")
    result = await db.execute(select(Subscription).where(Subscription.user_id == current_user.id))
    sub = result.scalar_one_or_none()
    if not sub:
        sub = Subscription(user_id=current_user.id)
        db.add(sub)
    sub.plan = PlanType(plan)
    sub.search_quota = quotas[plan]["search"]
    sub.analysis_quota = quotas[plan]["analysis"]
    sub.drafting_quota = quotas[plan]["drafting"]
    sub.advanced_ocr_quota = quotas[plan]["advanced_ocr"]
    sub.status = SubscriptionStatus.ACTIVE
    await db.commit()
    return {"status": "success", "plan": plan}
