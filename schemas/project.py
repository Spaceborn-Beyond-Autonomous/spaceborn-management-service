from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    team_id: Optional[int] = None
    owner_id: Optional[int] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    team_id: Optional[int] = None
    owner_id: Optional[int] = None

class ProjectRead(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True
