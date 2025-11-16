from pydantic import BaseModel, condecimal
from datetime import date
from typing import Optional

class RevenueBase(BaseModel):
    project_id: int
    amount: condecimal(max_digits=12, decimal_places=2)
    revenue_date: Optional[date] = None

class RevenueCreate(RevenueBase):
    pass

class RevenueUpdate(BaseModel):
    amount: Optional[condecimal(max_digits=12, decimal_places=2)] = None
    revenue_date: Optional[date] = None

class RevenueRead(RevenueBase):
    id: int
    class Config:
        from_attributes = True
