import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.v1.deps import get_current_user
from app.core.security import hash_password, verify_password
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool

class UpdateProfileRequest(BaseModel):
    full_name: str | None = None
    phone: str | None = None

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, description="كلمة المرور الجديدة يجب أن تكون 8 أحرف على الأقل")

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(id=current_user.id, email=current_user.email, full_name=current_user.full_name, role=current_user.role.value, is_active=current_user.is_active)

@router.put("/me", response_model=UserResponse)
async def update_profile(data: UpdateProfileRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.phone is not None:
        user.phone = data.phone
    await db.commit()
    await db.refresh(user)
    return UserResponse(id=user.id, email=user.email, full_name=user.full_name, role=user.role.value, is_active=user.is_active)

@router.put("/me/password")
async def change_password(data: ChangePasswordRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    if not verify_password(data.current_password, user.hashed_password):
        logger.warning("Password change failed: incorrect current password", extra={"user_id": user.id, "email": user.email})
        raise HTTPException(status_code=400, detail="كلمة المرور الحالية غير صحيحة")
    user.hashed_password = hash_password(data.new_password)
    await db.commit()
    logger.info("Password changed", extra={"user_id": user.id, "email": user.email})
    return {"status": "success", "detail": "تم تغيير كلمة المرور بنجاح"}
