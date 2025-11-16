from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import date
from db.base import Base

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.project import Project

class Revenue(Base):
    __tablename__ = "revenue" # type: ignore[assignment]
 
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    revenue_date: Mapped[date] = mapped_column(default=date.today, nullable=False)

    project: Mapped["Project"] = relationship("Project", back_populates="revenues")
