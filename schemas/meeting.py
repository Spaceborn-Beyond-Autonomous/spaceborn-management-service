from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from typing import List

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

class MeetingAttendanceCreate(BaseModel):
    user_ids: List[int]

class MeetingAttendanceRead(BaseModel):
    id: int
    meeting_id: int
    user_id: int
    attended: bool
    joined_at: Optional[datetime] = None
    created_at: datetime
    class Config:
        from_attributes = True

class UserAttendanceCount(BaseModel):
    user_id: int
    username: str
    email: str
    meetings_joined: int
    class Config:
        from_attributes = True
