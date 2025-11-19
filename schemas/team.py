from pydantic import BaseModel
from typing import Optional, List

from schemas.user import UserRead

class TeamBase(BaseModel):
    name: str

class TeamCreate(TeamBase):
    lead_id: Optional[int] = None
    member_ids: Optional[list[int]] = None

class TeamUpdate(BaseModel):
    name: Optional[str] = None
    lead_id: Optional[int] = None
    member_ids: Optional[list[int]] = None

class TeamRead(TeamBase):
    id: int
    lead_id: Optional[int] = None
    members: Optional[List[UserRead]] = None

    class Config:
        from_attributes = True
