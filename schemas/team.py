from pydantic import BaseModel, computed_field, ConfigDict
from typing import Optional, List

from schemas.user import UserRead


class TeamBase(BaseModel):
    name: str


class TeamCreate(TeamBase):
    lead_id: Optional[int] = None
    member_ids: Optional[list[int]] = None


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    lead_id: Optional[int] = None
    member_ids: Optional[list[int]] = None


class TeamRead(TeamBase):
    id: int
    lead_id: Optional[int] = None
    lead: Optional[UserRead] = None
    members: Optional[List[UserRead]] = None

    @computed_field
    @property
    def member_ids(self) -> List[int]:
        """Computed field to extract member IDs from members list"""
        if self.members:
            return [member.id for member in self.members]
        return []

    model_config = ConfigDict(from_attributes=True)
