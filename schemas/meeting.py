from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MeetingBase(BaseModel):
    project_id: int
    topic: str
    agenda: Optional[str] = None
    scheduled_at: datetime

class MeetingCreate(MeetingBase):
    pass

class MeetingUpdate(BaseModel):
    topic: Optional[str] = None
    agenda: Optional[str] = None
    scheduled_at: Optional[datetime] = None

class MeetingRead(MeetingBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True
