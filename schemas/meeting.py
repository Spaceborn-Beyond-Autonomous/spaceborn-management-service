from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from typing import List

from schemas.user import UserRead

class MeetingBase(BaseModel):
    title: str
    agenda: Optional[str] = None
    scheduled_at: datetime
    meeting_link: Optional[str] = None
    organizer: Optional[str] = None
    reminder_interval: int = 15
    notes: Optional[str] = None

class MeetingCreate(MeetingBase):
    attendees: Optional[List[int]] = None 

class MeetingUpdate(BaseModel):
    title: Optional[str] = None
    agenda: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    meeting_link: Optional[str] = None
    organizer: Optional[str] = None
    reminder_interval: Optional[int] = None
    notes: Optional[str] = None
    attendees: Optional[List[int]] = None

class MeetingAttendanceWithUser(BaseModel):
    id: int
    attended: bool
    joined_at: Optional[datetime] = None
    user: UserRead
    
    class Config:
        from_attributes = True

class MeetingRead(MeetingBase):
    id: int
    created_at: datetime
    attendances: List[MeetingAttendanceWithUser] = []
    class Config:
        from_attributes = True

class MeetingAttendanceCreate(BaseModel):
    attendees: Optional[List[int]] = None

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
