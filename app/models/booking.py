import enum

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Numeric, Enum, Index, func
from sqlalchemy.orm import relationship

from app.database import Base


class BookingStatus(str, enum.Enum):
    PENDING = "pending"      # seat reserved, awaiting payment
    CONFIRMED = "confirmed"  # payment succeeded
    CANCELLED = "cancelled"  # cancelled or payment failed -> seat freed up


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    show_id = Column(Integer, ForeignKey("shows.id", ondelete="CASCADE"), nullable=False, index=True)
    seat_id = Column(Integer, ForeignKey("seats.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(Enum(BookingStatus), default=BookingStatus.PENDING, nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    booked_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="bookings")
    show = relationship("Show", back_populates="bookings")
    seat = relationship("Seat", back_populates="bookings")
    payment = relationship("Payment", back_populates="booking", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        # This is the actual concurrency-safety mechanism for the whole system.
        #
        # A PARTIAL UNIQUE INDEX that only applies to rows where status != 'cancelled'.
        # This means the database itself physically refuses to store two active
        # (pending or confirmed) bookings for the same seat on the same show —
        # even if two requests hit this at the exact same millisecond.
        #
        # Why not just SELECT ... FOR UPDATE instead? Row locking only works on
        # rows that already exist. The very first booking attempt for a seat has
        # no existing row to lock, so FOR UPDATE alone can't prevent the initial
        # race. A unique constraint has no such gap: the second concurrent INSERT
        # is rejected by Postgres itself with an IntegrityError, which the booking
        # service catches and turns into a clean 409 Conflict response.
        #
        # Once a booking is cancelled, it's excluded from this index, so the seat
        # becomes bookable again for that show.
        Index(
            "uq_active_booking_per_seat_per_show",
            "show_id",
            "seat_id",
            unique=True,
            postgresql_where=(status != BookingStatus.CANCELLED),
            sqlite_where=(status != BookingStatus.CANCELLED),
        ),
    )


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, unique=True)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    transaction_ref = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    booking = relationship("Booking", back_populates="payment")
