# models/project.py
from sqlalchemy import String, ForeignKey, DateTime, Text, Enum, Integer, Float, Boolean, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from db.base import Base
from typing import TYPE_CHECKING
import enum

if TYPE_CHECKING:
    from models.team import Team
    from models.task import Task
    from models.revenue import Revenue
    from models.meeting import Meeting


class ProjectStatus(str, enum.Enum):
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ProjectPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Project(Base):
    __tablename__ = "projects"  # type: ignore[assignment]

    # Core Fields
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Status & Progress
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus),
        default=ProjectStatus.PLANNING,
        nullable=False,
        index=True
    )
    priority: Mapped[ProjectPriority] = mapped_column(
        Enum(ProjectPriority),
        default=ProjectPriority.MEDIUM,
        nullable=False,
        index=True
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Timeline
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Financial
    budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    spent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    
    # Organization
    team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"), 
        nullable=True,
        index=True
    )
    
    # Metadata
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    team: Mapped["Team"] = relationship("Team", back_populates="projects")
    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    revenues: Mapped[list["Revenue"]] = relationship("Revenue", back_populates="project", cascade="all, delete-orphan")
    meetings: Mapped[list["Meeting"]] = relationship("Meeting", back_populates="project", cascade="all, delete-orphan")

    @property
    def budget_remaining(self) -> float | None:
        """Calculate remaining budget"""
        if self.budget is None:
            return None
        return self.budget - self.spent

    @property
    def days_until_due(self) -> int | None:
        """Calculate days until due date"""
        if self.due_date is None:
            return None
        delta = self.due_date - datetime.now(timezone.utc)
        return delta.days

    @property
    def is_overdue(self) -> bool:
        """Check if project is overdue"""
        if self.due_date is None or self.status == ProjectStatus.COMPLETED:
            return False
        return datetime.now(timezone.utc) > self.due_date

    @property
    def completion_percentage(self) -> int:
        """Get overall completion based on tasks"""
        if not self.tasks:
            return self.progress
        
        completed_tasks = sum(1 for task in self.tasks if task.status == "done")
        return int((completed_tasks / len(self.tasks)) * 100) if self.tasks else 0
