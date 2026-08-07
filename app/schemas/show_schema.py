from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class ShowCreate(BaseModel):
    movie_id: int
    screen_id: int
    show_time: datetime
    price: Decimal


class ShowUpdate(BaseModel):
    show_time: Optional[datetime] = None
    price: Optional[Decimal] = None


class ShowOut(BaseModel):
    id: int
    movie_id: int
    screen_id: int
    show_time: datetime
    price: Decimal
    created_at: datetime

    class Config:
        from_attributes = True


class ShowDetailOut(ShowOut):
    movie_title: str
    theatre_name: str
    screen_name: str
