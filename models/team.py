from sqlalchemy import String, ForeignKey, Table, Column, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

team_members = Table(
    "team_members",
    Base.metadata,
    Column("team_id", ForeignKey("team.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("user.id", ondelete="CASCADE"), primary_key=True),
)

class Team(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    members: Mapped[list["User"]] = relationship(
        "User",
        secondary=team_members,
        back_populates="teams",
        lazy="selectin"
    )
    projects: Mapped[list["Project"]] = relationship("Project", back_populates="team", cascade="all, delete-orphan")
