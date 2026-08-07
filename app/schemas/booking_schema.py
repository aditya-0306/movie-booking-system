from datetime import datetime
from decimal import Decimal
from typing import List
from pydantic import BaseModel, Field

from app.models.booking import BookingStatus


class BookingCreate(BaseModel):
    show_id: int
    seat_ids: List[int] = Field(min_length=1, max_length=10)


class BookingOut(BaseModel):
    id: int
    show_id: int
    seat_id: int
    status: BookingStatus
    total_amount: Decimal
    booked_at: datetime

    class Config:
        from_attributes = True


class BookingBatchResult(BaseModel):
    """
    Returned by POST /bookings. Booking multiple seats is all-or-nothing:
    if ANY requested seat is already taken, the whole batch is rejected so the
    user doesn't end up with a partial, confusing booking.
    """
    bookings: List[BookingOut]
    unavailable_seat_ids: List[int] = []
