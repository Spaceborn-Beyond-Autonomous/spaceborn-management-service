from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.base import Base

from sqlalchemy.orm import declarative_base

Base = declarative_base()

if TYPE_CHECKING:
    from models.user import User
    from models.project import Project

# Association table
team_members = Table(
    "team_members",
    Base.metadata,
    Column("team_id", ForeignKey("team.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("user.id", ondelete="CASCADE"), primary_key=True),
)

class Team(Base):
    __tablename__ = "team"
    __allow_unmapped__ = True  # Add this line


    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("user.id", ondelete="SET NULL"))

    # Relationships
    lead: Mapped["User"] = relationship("User", back_populates="team_lead", foreign_keys=[lead_id])
    members: Mapped[list["User"]] = relationship(
        "User",
        secondary=team_members,
        back_populates="teams",
    )
    projects: Mapped[list["Project"]] = relationship("Project", back_populates="team")

    # Runtime-only attribute for response use
    member_ids: list[int] | None = None
