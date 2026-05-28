from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.api.v1.deps import get_current_user
from app.models.user import User

router = APIRouter()

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(id=current_user.id, email=current_user.email, full_name=current_user.full_name, role=current_user.role.value, is_active=current_user.is_active)
