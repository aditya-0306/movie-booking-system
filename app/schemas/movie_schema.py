from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class MovieCreate(BaseModel):
    title: str
    description: Optional[str] = None
    duration_minutes: int = Field(gt=0)
    genre: str
    language: str
    release_date: Optional[date] = None
    rating: float = Field(default=0.0, ge=0, le=10)
    poster_url: Optional[str] = None


class MovieUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    duration_minutes: Optional[int] = Field(default=None, gt=0)
    genre: Optional[str] = None
    language: Optional[str] = None
    release_date: Optional[date] = None
    rating: Optional[float] = Field(default=None, ge=0, le=10)
    poster_url: Optional[str] = None


class MovieOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    duration_minutes: int
    genre: str
    language: str
    release_date: Optional[date]
    rating: float
    poster_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
