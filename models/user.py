from sqlalchemy import String, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.base import Base
import enum

from sqlalchemy.orm import declarative_base

Base = declarative_base()

class RoleEnum(str, enum.Enum):
    ADMIN = "admin"
    CORE = "core"
    EMPLOYEE = "employee" 


class User(Base):
    __tablename__ = "users"  # Add this line
    
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[RoleEnum] = mapped_column(
        SQLEnum(RoleEnum, native_enum=False, length=20),
        nullable=False,
        default=RoleEnum.EMPLOYEE
    )
    
    # Add relationships if needed
    # teams: Mapped[list["Team"]] = relationship("Team", secondary="team_members", back_populates="members")
