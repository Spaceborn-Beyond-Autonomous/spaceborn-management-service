from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from models.user import RoleEnum

class UserBase(BaseModel):
    email: EmailStr
    username: str
    role: RoleEnum = RoleEnum.EMPLOYEE
    is_active: bool = True

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str = Field(min_length=6)
    role: RoleEnum = RoleEnum.EMPLOYEE

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email:Optional[EmailStr]=None
    role: Optional[RoleEnum] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

class UserRead(UserBase):
    id: int
    username: str
    email: EmailStr
    role: RoleEnum = RoleEnum.EMPLOYEE

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"

class TokenPayload(BaseModel):
    sub: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

