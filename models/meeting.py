from sqlalchemy import ForeignKey, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from db.base import Base
from typing import TYPE_CHECKING
from sqlalchemy.orm import DeclarativeBase

if TYPE_CHECKING:
    from models.project import Project
    from models.meeting_attendance import MeetingAttendance

class Meeting(Base):
    __tablename__ = "meetings" # type: ignore[assignment]
    
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), 
        nullable=False
    )
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    agenda: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    project: Mapped["Project"] = relationship("Project", back_populates="meetings")
    attendances: Mapped[list["MeetingAttendance"]] = relationship(
        back_populates="meeting",
        lazy="select"
    )
