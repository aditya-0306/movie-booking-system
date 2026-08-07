from sqlalchemy import Column, Integer, String, Text, Float, Date, DateTime, func
from sqlalchemy.orm import relationship

from app.database import Base


class Movie(Base):
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    duration_minutes = Column(Integer, nullable=False)
    genre = Column(String(100), nullable=False, index=True)
    language = Column(String(50), nullable=False, index=True)
    release_date = Column(Date, nullable=True)
    rating = Column(Float, default=0.0)
    poster_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    shows = relationship("Show", back_populates="movie", cascade="all, delete-orphan")
