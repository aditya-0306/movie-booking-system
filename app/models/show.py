from sqlalchemy import Column, Integer, ForeignKey, DateTime, Numeric, func
from sqlalchemy.orm import relationship

from app.database import Base


class Show(Base):
    __tablename__ = "shows"

    id = Column(Integer, primary_key=True, index=True)
    movie_id = Column(Integer, ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, index=True)
    screen_id = Column(Integer, ForeignKey("screens.id", ondelete="CASCADE"), nullable=False, index=True)
    show_time = Column(DateTime(timezone=True), nullable=False, index=True)
    price = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    movie = relationship("Movie", back_populates="shows")
    screen = relationship("Screen", back_populates="shows")
    bookings = relationship("Booking", back_populates="show", cascade="all, delete-orphan")
