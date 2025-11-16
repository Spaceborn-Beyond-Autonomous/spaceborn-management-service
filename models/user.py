import enum
from sqlalchemy import String, Enum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.base import Base

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.team import Team


class RoleEnum(str, enum.Enum):
    admin = "admin"
    core = "core"
    employee = "employee"

class User(Base):
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum, name="role_enum"), default=RoleEnum.employee, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    teams: Mapped[list["Team"]] = relationship(
        "Team",
        secondary="team_members",
        back_populates="members",
        lazy="selectin"
    )
