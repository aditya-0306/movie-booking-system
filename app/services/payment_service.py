import secrets
from sqlalchemy.orm import Session

from app.middleware.exception_handler import AppException
from app.models.booking import Booking, BookingStatus, Payment, PaymentStatus
from app.models.user import User, UserRole
from app.repositories.booking_repository import BookingRepository
from app.schemas.payment_schema import PaymentRequest


class PaymentService:
    """
    Mock payment gateway. No real payment provider is called -- this
    simulates the success/failure branching a real integration (Stripe,
    Razorpay, etc.) would have, including the important part most tutorial
    projects skip: what happens to the SEAT when payment fails.
    """

    def __init__(self, db: Session):
        self.db = db
        self.booking_repo = BookingRepository(db)

    def process_payment(self, user: User, data: PaymentRequest) -> Payment:
        booking = self.booking_repo.get_by_id(data.booking_id)
        if not booking:
            raise AppException(404, "Booking not found")

        if booking.user_id != user.id and user.role != UserRole.ADMIN:
            raise AppException(403, "You can only pay for your own bookings")

        if booking.status != BookingStatus.PENDING:
            raise AppException(400, f"Booking is not payable (current status: {booking.status.value})")

        existing_payment = (
            self.db.query(Payment).filter(Payment.booking_id == booking.id).first()
        )
        if existing_payment:
            raise AppException(400, "A payment already exists for this booking")

        succeeded = not data.simulate_failure

        payment = Payment(
            booking_id=booking.id,
            amount=booking.total_amount,
            status=PaymentStatus.SUCCESS if succeeded else PaymentStatus.FAILED,
            transaction_ref=f"MOCK-{secrets.token_hex(8).upper()}",
        )
        self.db.add(payment)

        if succeeded:
            booking.status = BookingStatus.CONFIRMED
        else:
            # Payment failed -> release the seat by cancelling the booking.
            # Because our unique index excludes cancelled bookings, this seat
            # immediately becomes bookable by someone else again.
            booking.status = BookingStatus.CANCELLED

        self.db.commit()
        self.db.refresh(payment)
        return payment
