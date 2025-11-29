from sqlalchemy import Integer, String, Boolean, ForeignKey, Enum as SQLEnum, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import enum
from db.base import Base
# Use string forward reference for User to avoid circular imports if needed
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.user import User

class NotificationType(str, enum.Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"

class Notification(Base):
    __tablename__ = "notifications"  # type: ignore[assignment]

    # Use Mapped[] types so Pylance knows these are actual values (int, str, bool), not Columns
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(String, nullable=False)
    
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    
    type: Mapped[NotificationType] = mapped_column(
        SQLEnum(NotificationType, native_enum=False), 
        default=NotificationType.INFO
    )
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notifications")