from pydantic import BaseModel
from typing import Optional, List

class TeamBase(BaseModel):
    name: str

class TeamCreate(TeamBase):
    member_ids: Optional[list[int]] = None

class TeamUpdate(BaseModel):
    name: Optional[str] = None
    member_ids: Optional[list[int]] = None

class TeamRead(TeamBase):
    id: int
    member_ids: list[int] = []
    class Config:
        from_attributes = True
