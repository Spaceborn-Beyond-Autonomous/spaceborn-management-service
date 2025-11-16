from pydantic import BaseModel, Field
from datetime import date
from typing import Optional
from decimal import Decimal


class RevenueBase(BaseModel):
    project_id: int
    amount: Decimal = Field(max_digits=12, decimal_places=2)
    revenue_date: Optional[date] = None


class RevenueCreate(RevenueBase):
    pass


class RevenueUpdate(BaseModel):
    amount: Optional[Decimal] = Field(None, max_digits=12, decimal_places=2)
    revenue_date: Optional[date] = None


class RevenueRead(RevenueBase):
    id: int
    model_config = {"from_attributes": True}
