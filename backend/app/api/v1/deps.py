from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.core.security import verify_token
from app.models.user import User
from app.models.subscription import Subscription

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="رمز غير صالح")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="رمز غير صالح")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="حساب غير نشط")
    return user

async def check_search_quota(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Subscription:
    result = await db.execute(select(Subscription).where(Subscription.user_id == current_user.id))
    sub = result.scalar_one_or_none()
    if not sub:
        sub = Subscription(user_id=current_user.id)
        if current_user.role.value == "admin":
            sub.search_quota = 99999
        db.add(sub)
        await db.commit()
        await db.refresh(sub)
    if current_user.role.value == "admin":
        return sub
    if sub.searches_used >= sub.search_quota:
        raise HTTPException(status_code=403, detail="لقد استنفذت حصة البحث الشهرية. قم بترقية خطتك")
    return sub

async def check_analysis_quota(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Subscription:
    result = await db.execute(select(Subscription).where(Subscription.user_id == current_user.id))
    sub = result.scalar_one_or_none()
    if not sub:
        sub = Subscription(user_id=current_user.id)
        if current_user.role.value == "admin":
            sub.analysis_quota = 99999
        db.add(sub)
        await db.commit()
        await db.refresh(sub)
    if current_user.role.value == "admin":
        return sub
    if sub.analyses_used >= sub.analysis_quota:
        raise HTTPException(status_code=403, detail="لقد استنفذت حصة التحليل الشهرية. قم بترقية خطتك")
    return sub

async def check_drafting_quota(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Subscription:
    result = await db.execute(select(Subscription).where(Subscription.user_id == current_user.id))
    sub = result.scalar_one_or_none()
    if not sub:
        sub = Subscription(user_id=current_user.id)
        if current_user.role.value == "admin":
            sub.drafting_quota = 99999
        db.add(sub)
        await db.commit()
        await db.refresh(sub)
    if current_user.role.value == "admin":
        return sub
    if sub.drafts_used >= sub.drafting_quota:
        raise HTTPException(status_code=403, detail="لقد استنفذت حصة الصياغة الشهرية. قم بترقية خطتك")
    return sub

async def get_admin_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="رمز غير صالح")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="رمز غير صالح")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="حساب غير نشط")
    if user.role.value != "admin":
        raise HTTPException(status_code=403, detail="صلاحية غير كافية")
    return user
