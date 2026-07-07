from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
from pydantic import BaseModel, EmailStr, Field
from datetime import timedelta
from app.db.session import get_db
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, verify_token
from app.models.user import User, UserRole
from app.services.email_service import email_service

logger = logging.getLogger(__name__)
router = APIRouter()

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, description="كلمة المرور يجب أن تكون 8 أحرف على الأقل")
    full_name: str
    phone: str | None = None
    role: UserRole = UserRole.CLIENT

    class Config:
        json_schema_extra = {"role": "ignored — always set to CLIENT for security"}

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserData(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserData

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/register")
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="بريد إلكتروني موجود مسبقاً")
    user = User(email=data.email, hashed_password=hash_password(data.password), full_name=data.full_name, phone=data.phone, role=UserRole.CLIENT)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("User registered", extra={"user_id": user.id, "email": user.email, "ip": "unknown"})
    token_data = {"sub": user.id, "role": user.role.value}
    return AuthResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        user=UserData(id=user.id, email=user.email, full_name=user.full_name, role=user.role.value, is_active=user.is_active),
    )

@router.post("/login")
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        logger.warning("Failed login attempt", extra={"email": data.email})
        raise HTTPException(status_code=401, detail="بريد إلكتروني أو كلمة مرور غير صحيحة")
    if not user.is_active:
        logger.warning("Login blocked: inactive account", extra={"user_id": user.id, "email": data.email})
        raise HTTPException(status_code=403, detail="حساب غير نشط")
    logger.info("User logged in", extra={"user_id": user.id, "email": user.email})
    token_data = {"sub": user.id, "role": user.role.value}
    return AuthResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        user=UserData(id=user.id, email=user.email, full_name=user.full_name, role=user.role.value, is_active=user.is_active),
    )

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, description="كلمة المرور الجديدة يجب أن تكون 8 أحرف على الأقل")

class VerifyEmailRequest(BaseModel):
    token: str

@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user:
        return {"status": "success", "detail": "إذا كان البريد موجوداً، سيتم إرسال رابط إعادة التعيين"}
    logger.info("Password reset requested", extra={"user_id": user.id, "email": data.email})
    reset_token = create_access_token({"sub": user.id, "purpose": "reset"}, expires_delta=timedelta(hours=1))
    background_tasks.add_task(email_service.send_password_reset, data.email, reset_token)
    return {"status": "success", "detail": "تم إرسال رابط إعادة تعيين كلمة المرور إلى بريدك الإلكتروني"}

@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    payload = verify_token(data.token)
    if not payload or payload.get("purpose") != "reset":
        raise HTTPException(status_code=401, detail="الرمز غير صالح أو منتهي الصلاحية")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="الرمز غير صالح")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    user.hashed_password = hash_password(data.new_password)
    await db.commit()
    logger.info("Password reset completed", extra={"user_id": user.id, "email": user.email})
    return {"status": "success", "detail": "تم إعادة تعيين كلمة المرور بنجاح"}

@router.post("/verify-email")
async def verify_email(data: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    payload = verify_token(data.token)
    if not payload or payload.get("purpose") != "verify":
        raise HTTPException(status_code=401, detail="الرمز غير صالح أو منتهي الصلاحية")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="الرمز غير صالح")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    user.is_verified = True
    await db.commit()
    return {"status": "success", "detail": "تم تأكيد البريد الإلكتروني بنجاح"}

@router.post("/refresh")
async def refresh_token(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = verify_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="رمز التحديث غير صالح أو منتهي الصلاحية")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="رمز التحديث غير صالح")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="المستخدم غير موجود أو غير نشط")
    token_data = {"sub": user.id, "role": user.role.value}
    return AuthResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        user=UserData(id=user.id, email=user.email, full_name=user.full_name, role=user.role.value, is_active=user.is_active),
    )
