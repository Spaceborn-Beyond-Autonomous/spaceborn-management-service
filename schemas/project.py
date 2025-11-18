from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class ProjectStatus(str, Enum):
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ProjectPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    
    # Status & Progress
    status: ProjectStatus = Field(default=ProjectStatus.PLANNING)
    priority: ProjectPriority = Field(default=ProjectPriority.MEDIUM)
    progress: int = Field(default=0, ge=0, le=100)
    
    # Timeline
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Financial
    budget: Optional[float] = Field(None, ge=0)
    spent: float = Field(default=0.0, ge=0)
    
    # Organization
    team_id: Optional[int] = None
    
    # Metadata
    is_archived: bool = Field(default=False)
    tags: Optional[list[str]] = Field(default_factory=list)


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    status: Optional[ProjectStatus] = ProjectStatus.PLANNING
    priority: Optional[ProjectPriority] = ProjectPriority.MEDIUM
    progress: Optional[int] = Field(default=0, ge=0, le=100)
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    budget: Optional[float] = Field(None, ge=0)
    team_id: Optional[int] = None
    tags: Optional[list[str]] = Field(default_factory=list)


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    status: Optional[ProjectStatus] = None
    priority: Optional[ProjectPriority] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    budget: Optional[float] = Field(None, ge=0)
    spent: Optional[float] = Field(None, ge=0)
    team_id: Optional[int] = None
    is_archived: Optional[bool] = None
    tags: Optional[list[str]] = None


class ProjectRead(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    # Computed fields
    budget_remaining: Optional[float] = None
    days_until_due: Optional[int] = None
    is_overdue: bool = False
    
    class Config:
        from_attributes = True
