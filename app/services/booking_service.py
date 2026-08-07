import math
from decimal import Decimal
from sqlalchemy.orm import Session

from app.middleware.exception_handler import AppException
from app.models.booking import Booking, BookingStatus
from app.models.user import User, UserRole
from app.repositories.booking_repository import BookingRepository
from app.repositories.show_repository import ShowRepository
from app.repositories.theatre_repository import TheatreRepository
from app.schemas.booking_schema import BookingCreate, BookingBatchResult
from app.schemas.common_schema import PaginationParams


class BookingService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = BookingRepository(db)
        self.show_repo = ShowRepository(db)
        self.theatre_repo = TheatreRepository(db)

    def create_booking(self, user: User, data: BookingCreate) -> BookingBatchResult:
        show = self.show_repo.get_by_id(data.show_id)
        if not show:
            raise AppException(404, "Show not found")

        # Validate every requested seat actually belongs to this show's screen
        # before attempting to reserve anything.
        valid_seat_ids = {s.id for s in self.theatre_repo.list_seats_for_screen(show.screen_id)}
        invalid = [sid for sid in data.seat_ids if sid not in valid_seat_ids]
        if invalid:
            raise AppException(400, f"Seat IDs not valid for this show's screen: {invalid}")

        reserved, unavailable = self.repo.try_reserve_seats(
            user_id=user.id,
            show_id=data.show_id,
            seat_ids=data.seat_ids,
            amount_per_seat=show.price,
        )

        if unavailable:
            raise AppException(
                409,
                f"Seat(s) already booked for this show: {unavailable}. No seats were reserved.",
            )

        return BookingBatchResult(bookings=reserved, unavailable_seat_ids=[])

    def get_booking(self, booking_id: int) -> Booking:
        booking = self.repo.get_by_id(booking_id)
        if not booking:
            raise AppException(404, "Booking not found")
        return booking

    def cancel_booking(self, user: User, booking_id: int) -> Booking:
        booking = self.get_booking(booking_id)

        if booking.user_id != user.id and user.role != UserRole.ADMIN:
            raise AppException(403, "You can only cancel your own bookings")

        if booking.status == BookingStatus.CANCELLED:
            raise AppException(400, "Booking is already cancelled")

        booking.status = BookingStatus.CANCELLED
        return self.repo.update(booking)

    def list_my_bookings(self, user: User, pagination: PaginationParams) -> dict:
        items, total = self.repo.list_for_user(user.id, pagination.offset, pagination.page_size)
        return {
            "items": items,
            "total": total,
            "page": pagination.page,
            "page_size": pagination.page_size,
            "total_pages": math.ceil(total / pagination.page_size) if total else 0,
        }
