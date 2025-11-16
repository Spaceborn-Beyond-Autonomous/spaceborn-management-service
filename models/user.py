from typing import TYPE_CHECKING
from sqlalchemy import String, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.base import Base
import enum

if TYPE_CHECKING:
    from models.team import Team

class RoleEnum(str, enum.Enum):
    ADMIN = "admin"
    CORE = "core"
    EMPLOYEE = "employee"


class User(Base):
    __tablename__ = "users"  # type: ignore[assignment]
    
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[RoleEnum] = mapped_column(
        SQLEnum(RoleEnum, native_enum=False, length=20),
        nullable=False,
        default=RoleEnum.EMPLOYEE
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    
    # Teams this user leads (automatically returns empty list if none)
    team_lead: Mapped[list["Team"]] = relationship(
        "Team",
        back_populates="lead",
        foreign_keys="[Team.lead_id]"
    )
    
    # Teams this user is a member of (automatically returns empty list if none)
    teams: Mapped[list["Team"]] = relationship(
        "Team",
        secondary="team_members",
        back_populates="members"
    )