from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from app.db.session import get_db
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.models.user import User, UserRole

router = APIRouter()

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str | None = None
    role: UserRole = UserRole.CLIENT

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

@router.post("/register", response_model=TokenResponse)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="?????? ???? ??????")
    user = User(email=data.email, hashed_password=hash_password(data.password), full_name=data.full_name, phone=data.phone, role=data.role)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token_data = {"sub": user.id, "role": user.role.value}
    return TokenResponse(access_token=create_access_token(token_data), refresh_token=create_refresh_token(token_data))

@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="?????? ?????? ??? ?????")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="?????? ????")
    token_data = {"sub": user.id, "role": user.role.value}
    return TokenResponse(access_token=create_access_token(token_data), refresh_token=create_refresh_token(token_data))
