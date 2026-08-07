from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

from app.models.theatre import SeatType


class TheatreCreate(BaseModel):
    name: str
    city: str
    address: Optional[str] = None


class TheatreUpdate(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None


class TheatreOut(BaseModel):
    id: int
    name: str
    city: str
    address: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ScreenCreate(BaseModel):
    theatre_id: int
    name: str


class ScreenOut(BaseModel):
    id: int
    theatre_id: int
    name: str
    total_seats: int
    created_at: datetime

    class Config:
        from_attributes = True


class SeatCreate(BaseModel):
    seat_number: str
    seat_type: SeatType = SeatType.REGULAR


class SeatGenerateRequest(BaseModel):
    """Convenience endpoint: auto-generate a grid of seats instead of creating them one by one."""
    rows: int
    seats_per_row: int
    premium_rows: int = 0  # first N rows are marked premium


class SeatOut(BaseModel):
    id: int
    screen_id: int
    seat_number: str
    seat_type: SeatType

    class Config:
        from_attributes = True


class SeatAvailability(BaseModel):
    seat_id: int
    seat_number: str
    seat_type: SeatType
    is_available: bool
