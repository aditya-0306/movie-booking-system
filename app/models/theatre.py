import enum

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.database import Base


class Theatre(Base):
    __tablename__ = "theatres"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    city = Column(String(100), nullable=False, index=True)
    address = Column(String(300), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    screens = relationship("Screen", back_populates="theatre", cascade="all, delete-orphan")


class Screen(Base):
    __tablename__ = "screens"

    id = Column(Integer, primary_key=True, index=True)
    theatre_id = Column(Integer, ForeignKey("theatres.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    total_seats = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    theatre = relationship("Theatre", back_populates="screens")
    seats = relationship("Seat", back_populates="screen", cascade="all, delete-orphan")
    shows = relationship("Show", back_populates="screen", cascade="all, delete-orphan")


class SeatType(str, enum.Enum):
    REGULAR = "regular"
    PREMIUM = "premium"


class Seat(Base):
    __tablename__ = "seats"
    __table_args__ = (UniqueConstraint("screen_id", "seat_number", name="uq_screen_seat_number"),)

    id = Column(Integer, primary_key=True, index=True)
    screen_id = Column(Integer, ForeignKey("screens.id", ondelete="CASCADE"), nullable=False, index=True)
    seat_number = Column(String(10), nullable=False)  # e.g. "A1", "B12"
    seat_type = Column(Enum(SeatType), default=SeatType.REGULAR, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    screen = relationship("Screen", back_populates="seats")
    bookings = relationship("Booking", back_populates="seat")
