from sqlalchemy import ForeignKey, DateTime, String, Text, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from db.base import Base
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from models.project import Project
    from models.meeting_attendance import MeetingAttendance
    from models.user import User

class Meeting(Base):
    __tablename__ = "meetings" # type: ignore[assignment]

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    agenda: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    meeting_link: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    organizer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reminder_interval: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    # Relationship to MeetingAttendance association
    attendances: Mapped[List["MeetingAttendance"]] = relationship(
        back_populates="meeting",
        lazy="select",
        cascade="all, delete-orphan"
    )

    # Convenient access to users attending the meeting through attendances
    attendees: Mapped[List["User"]] = relationship(
        "User",
        secondary="meeting_attendances",
        viewonly=True,
        back_populates="meetings"
    )
