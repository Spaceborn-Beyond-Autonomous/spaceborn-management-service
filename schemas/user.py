from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from app.models.user import RoleEnum

class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: RoleEnum = RoleEnum.employee
    is_active: bool = True

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str = Field(min_length=6)
    role: RoleEnum = RoleEnum.employee

class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[RoleEnum] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

class UserRead(UserBase):
    id: int
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"

class TokenPayload(BaseModel):
    sub: str
