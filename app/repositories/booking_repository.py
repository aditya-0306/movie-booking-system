from typing import Optional
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.booking import Booking, BookingStatus


class BookingRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, booking_id: int) -> Optional[Booking]:
        return self.db.query(Booking).filter(Booking.id == booking_id).first()

    def get_active_bookings_for_show(self, show_id: int) -> list[Booking]:
        return (
            self.db.query(Booking)
            .filter(
                Booking.show_id == show_id,
                Booking.status != BookingStatus.CANCELLED,
            )
            .all()
        )

    def try_reserve_seats(
        self, user_id: int, show_id: int, seat_ids: list[int], amount_per_seat
    ) -> tuple[list[Booking], list[int]]:
        """
        Attempts to reserve every seat in seat_ids as one all-or-nothing batch.

        How the concurrency safety actually works:
        Each seat is inserted as its own row inside a SAVEPOINT. The partial
        unique index defined on the Booking model (show_id, seat_id) WHERE
        status != 'cancelled' means Postgres itself rejects a duplicate active
        booking for a seat that's already taken -- even if another request
        grabbed it a millisecond earlier. We catch that IntegrityError per
        seat, roll back just that savepoint, and record the seat as
        unavailable. If ANY seat in the batch is unavailable, we roll back
        the entire outer transaction so the user never ends up with a
        confusing partial booking (e.g. 2 of the 3 seats they asked for).
        """
        successfully_reserved: list[Booking] = []
        unavailable_seat_ids: list[int] = []

        for seat_id in seat_ids:
            savepoint = self.db.begin_nested()
            booking = Booking(
                user_id=user_id,
                show_id=show_id,
                seat_id=seat_id,
                status=BookingStatus.PENDING,
                total_amount=amount_per_seat,
            )
            self.db.add(booking)
            try:
                self.db.flush()  # forces the INSERT (and the unique constraint check) now
                successfully_reserved.append(booking)
            except IntegrityError:
                savepoint.rollback()
                unavailable_seat_ids.append(seat_id)

        if unavailable_seat_ids:
            # All-or-nothing: undo the whole attempt, including any seats
            # that DID succeed above, and report which ones were the problem.
            self.db.rollback()
            return [], unavailable_seat_ids

        self.db.commit()
        for b in successfully_reserved:
            self.db.refresh(b)
        return successfully_reserved, []

    def update(self, booking: Booking) -> Booking:
        self.db.commit()
        self.db.refresh(booking)
        return booking

    def list_for_user(self, user_id: int, offset: int, limit: int) -> tuple[list[Booking], int]:
        query = self.db.query(Booking).filter(Booking.user_id == user_id)
        total = query.count()
        items = query.order_by(Booking.booked_at.desc()).offset(offset).limit(limit).all()
        return items, total
