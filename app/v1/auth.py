from fastapi import APIRouter, Depends
from app.deps import get_current_user
from schemas.user import UserRead
from models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/verify", response_model=UserRead)
async def verify_token(user: User = Depends(get_current_user)):
    return user
