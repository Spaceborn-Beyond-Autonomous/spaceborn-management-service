from typing import AsyncGenerator, Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.session import AsyncSessionLocal
from core.security import decode_token
from schemas.user import TokenPayload
from models.user import User, RoleEnum
from services.cache_service import UserCacheService


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")


async def get_session_dep() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_session_dep)]
) -> User:
    """Get current user with Redis caching"""
    
    # Decode JWT token
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    data = TokenPayload(**payload)
    user_id = int(data.sub)
    
    # Try to get from cache first
    cached_user = await UserCacheService.get_user(user_id)
    if cached_user:
        print(f"✓ Cache HIT for user {user_id}")
        # Convert cached dict back to User model
        # Convert role string back to RoleEnum
        role = cached_user["role"]
        if isinstance(role, str):
            role = RoleEnum(role)  # Convert string to enum
        
        user = User(
            id=cached_user["id"],
            email=cached_user["email"],
            username=cached_user["username"],
            role=role,  # Use the converted enum
            is_active=cached_user["is_active"],
            hashed_password=""
        )
        return user
    
    print(f"✗ Cache MISS for user {user_id}")
    
    # Cache miss - query database
    q = await session.execute(
        select(User).where(User.id == user_id, User.is_active == True)
    )
    user = q.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User inactive or not found"
        )
    
    # Cache the user for next requests
    await UserCacheService.set_user(user)
    
    return user


def require_roles(*roles: RoleEnum):
    async def dep(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return user
    return dep


# Shorthand dependencies
AdminOnly = require_roles(RoleEnum.ADMIN)
CoreOrAdmin = require_roles(RoleEnum.ADMIN, RoleEnum.CORE)
AnyAuthenticated = get_current_user
