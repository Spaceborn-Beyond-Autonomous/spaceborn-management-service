from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from app.deps import get_session_dep, AdminOnly, get_current_user
from schemas.user import LoginRequest, UserRead, UserCreate, UserUpdate, Token
from core.security import hash_password, verify_password, create_access_token
from models.user import User, RoleEnum
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/users", tags=["users"])

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
    return user

@router.post("/login", response_model=Token)
async def login(
    request: LoginRequest, 
    session: AsyncSession = Depends(get_session_dep)
):    
    print(request.email)
    query = await session.execute(select(User).where(User.email == request.email))
    user = query.scalar_one_or_none()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    token = create_access_token(subject=user.id)
    return {"access_token": token, "token_type": "bearer"}

@router.get("/", response_model=list[UserRead], dependencies=[Depends(AdminOnly)])
async def list_users(
    session: AsyncSession = Depends(get_session_dep),
    include_inactive: bool = False  # Query parameter
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
async def update_user(user_id: int, payload: UserUpdate, session: AsyncSession = Depends(get_session_dep)):
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.password:
        user.hashed_password = hash_password(payload.password)
    if payload.username is not None:
        user.username = payload.username
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    await session.commit()
    await session.refresh(user)
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(AdminOnly)])
async def delete_user(user_id: int, session: AsyncSession = Depends(get_session_dep)):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Soft delete: set is_active to False instead of deleting
    user.is_active = False
    await session.commit()


@router.patch("/{user_id}/activate", response_model=UserRead, dependencies=[Depends(AdminOnly)])
async def activate_user(user_id: int, session: AsyncSession = Depends(get_session_dep)):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = True
    await session.commit()
    await session.refresh(user)
    return user


