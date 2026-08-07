from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.payment_schema import PaymentRequest, PaymentOut
from app.services.auth_service import get_current_user
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def process_payment(
    payload: PaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mock payment gateway. Set simulate_failure=true in the request body to
    test the failure path -- the booking's seat is released back into the
    available pool when payment fails, exactly like a real gateway
    integration would need to handle.
    """
    return PaymentService(db).process_payment(current_user, payload)
