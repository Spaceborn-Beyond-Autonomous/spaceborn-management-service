from sqlalchemy import ForeignKey, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from db.base import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.meeting import Meeting
    from models.user import User

class MeetingAttendance(Base):
    __tablename__ = "meeting_attendances"  # type: ignore[assignment]

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    attended: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    joined_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="attendances")
    user: Mapped["User"] = relationship("User", back_populates="meeting_attendances")
