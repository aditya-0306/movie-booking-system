from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel

from app.models.booking import PaymentStatus


class PaymentRequest(BaseModel):
    booking_id: int
    simulate_failure: bool = False  # lets you test the failure path on purpose


class PaymentOut(BaseModel):
    id: int
    booking_id: int
    amount: Decimal
    status: PaymentStatus
    transaction_ref: str | None
    created_at: datetime

    class Config:
        from_attributes = True
