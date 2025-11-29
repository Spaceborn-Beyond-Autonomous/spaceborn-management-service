import time
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.deps import CoreOrAdmin, get_session_dep, AdminOnly, get_current_user, AnyAuthenticated
from schemas.user import LoginRequest, UserRead, UserCreate, UserUpdate, Token
from core.security import hash_password, verify_password, create_access_token
from models.user import User
from services.cache_service import UserCacheService
from pydantic import BaseModel

router = APIRouter(prefix="/users", tags=["users"])

# --- AUTH ENDPOINTS ---

@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(AdminOnly)])
async def register_user(payload: UserCreate, session: AsyncSession = Depends(get_session_dep)):
    exists = (await session.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=409, detail="Email already registered")
    
    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
        role=payload.role
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    
    await UserCacheService.set_user(user)
    return user

@router.post("/login", response_model=Token)
async def login(
    request: LoginRequest, 
    session: AsyncSession = Depends(get_session_dep)
):    
    # --- PERFORMANCE DEBUG START ---
    t0 = time.time()
    
    query = await session.execute(select(User).where(User.email == request.email))
    user = query.scalar_one_or_none()
    
    t1 = time.time()
    print(f"⏱️ DB Query took: {t1 - t0:.4f}s") # Check if DB is slow

    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    # Verify Password (Computing Hash)
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    t2 = time.time()
    print(f"⏱️ Password Hashing took: {t2 - t1:.4f}s") # Check if CPU is slow

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Account is inactive")
    
    # Cache Warming
    try:
        await UserCacheService.set_user(user)
        t3 = time.time()
        print(f"⏱️ Redis Cache took: {t3 - t2:.4f}s") # Check if Redis is slow
    except Exception as e:
        print(f"⚠️ Redis Error (ignoring): {e}")

    token = create_access_token(subject=user.id)
    return {"access_token": token, "token_type": "bearer"}


# --- PROFILE & SETTINGS ENDPOINTS (NEW) ---

class UpdateProfileRequest(BaseModel):
    username: str | None = None
    email: str | None = None

@router.patch("/me", response_model=UserRead)
async def update_my_profile(
    payload: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_dep)
):
    """Allows a user to update their own basic info"""
    if payload.username:
        user.username = payload.username
    if payload.email:
        user.email = payload.email
    
    await session.commit()
    await session.refresh(user)
    
    # Update cache
    await UserCacheService.set_user(user)
    
    return user

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    payload: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_dep)
):
    """Allows a user to change their password"""
    # 1. Verify current password
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid current password")
    
    # 2. Update to new password
    user.hashed_password = hash_password(payload.new_password)
    
    await session.commit()
    return {"message": "Password updated successfully"}


# --- ADMIN MANAGEMENT ENDPOINTS ---

@router.get("/", response_model=list[UserRead], dependencies=[Depends(CoreOrAdmin)])
async def list_users(
    session: AsyncSession = Depends(get_session_dep),
    include_inactive: bool = False
):
    query = select(User)
    if not include_inactive:
        query = query.where(User.is_active == True)
    users = (await session.execute(query)).scalars().all()
    return users

@router.get("/me", response_model=UserRead)
async def get_me(user: User = Depends(get_current_user)):
    return user

@router.get("/{user_id}", response_model=UserRead, dependencies=[Depends(AdminOnly)])
async def get_user(user_id: int, session: AsyncSession = Depends(get_session_dep)):
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.patch("/{user_id}", response_model=UserRead, dependencies=[Depends(AdminOnly)])
async def update_user(
    user_id: int,
    payload: UserUpdate,
    session: AsyncSession = Depends(get_session_dep)
):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if payload.username is not None:
        user.username = payload.username
    if payload.email is not None:
        user.email = payload.email
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.password:
        user.hashed_password = hash_password(payload.password)
    
    await session.commit()
    await session.refresh(user)
    await UserCacheService.invalidate_user(user_id)
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(AdminOnly)])
async def delete_user(user_id: int, session: AsyncSession = Depends(get_session_dep)):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    await session.commit()
    await UserCacheService.invalidate_user(user_id)