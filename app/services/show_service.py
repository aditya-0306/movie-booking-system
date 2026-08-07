import math
from datetime import date
from typing import Optional
from sqlalchemy.orm import Session

from app.middleware.exception_handler import AppException
from app.models.show import Show
from app.models.movie import Movie
from app.models.theatre import Screen, Theatre
from app.repositories.show_repository import ShowRepository
from app.repositories.theatre_repository import TheatreRepository
from app.repositories.booking_repository import BookingRepository
from app.schemas.show_schema import ShowCreate, ShowUpdate
from app.schemas.common_schema import PaginationParams
from app.schemas.theatre_schema import SeatAvailability
from app.services.cache_service import get_cached, set_cached, invalidate_show_cache, SHOW_DETAIL_PREFIX
from app.config import settings


class ShowService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ShowRepository(db)
        self.theatre_repo = TheatreRepository(db)
        self.booking_repo = BookingRepository(db)

    def create_show(self, data: ShowCreate) -> Show:
        movie = self.db.query(Movie).filter(Movie.id == data.movie_id).first()
        if not movie:
            raise AppException(404, "Movie not found")
        screen = self.theatre_repo.get_screen(data.screen_id)
        if not screen:
            raise AppException(404, "Screen not found")

        show = Show(**data.model_dump())
        return self.repo.create(show)

    def get_show(self, show_id: int) -> Show:
        show = self.repo.get_by_id(show_id)
        if not show:
            raise AppException(404, "Show not found")
        return show

    def get_show_detail(self, show_id: int) -> dict:
        cache_key = f"{SHOW_DETAIL_PREFIX}{show_id}"
        cached = get_cached(cache_key)
        if cached:
            return cached

        show = self.get_show(show_id)
        movie = self.db.query(Movie).filter(Movie.id == show.movie_id).first()
        screen = self.theatre_repo.get_screen(show.screen_id)
        theatre = self.theatre_repo.get_theatre(screen.theatre_id)

        result = {
            "id": show.id,
            "movie_id": show.movie_id,
            "screen_id": show.screen_id,
            "show_time": show.show_time,
            "price": show.price,
            "created_at": show.created_at,
            "movie_title": movie.title,
            "theatre_name": theatre.name,
            "screen_name": screen.name,
        }
        set_cached(cache_key, result, settings.SHOW_CACHE_TTL_SECONDS)
        return result

    def list_shows(
        self,
        pagination: PaginationParams,
        movie_id: Optional[int] = None,
        theatre_id: Optional[int] = None,
        show_date: Optional[date] = None,
    ) -> dict:
        items, total = self.repo.list(
            offset=pagination.offset,
            limit=pagination.page_size,
            movie_id=movie_id,
            theatre_id=theatre_id,
            show_date=show_date,
        )
        return {
            "items": items,
            "total": total,
            "page": pagination.page,
            "page_size": pagination.page_size,
            "total_pages": math.ceil(total / pagination.page_size) if total else 0,
        }

    def get_seat_availability(self, show_id: int) -> list[SeatAvailability]:
        show = self.get_show(show_id)
        all_seats = self.theatre_repo.list_seats_for_screen(show.screen_id)
        active_bookings = self.booking_repo.get_active_bookings_for_show(show_id)
        booked_seat_ids = {b.seat_id for b in active_bookings}

        return [
            SeatAvailability(
                seat_id=seat.id,
                seat_number=seat.seat_number,
                seat_type=seat.seat_type,
                is_available=seat.id not in booked_seat_ids,
            )
            for seat in all_seats
        ]

    def update_show(self, show_id: int, data: ShowUpdate) -> Show:
        show = self.get_show(show_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(show, field, value)
        show = self.repo.update(show)
        invalidate_show_cache(show_id)
        return show

    def delete_show(self, show_id: int) -> None:
        show = self.get_show(show_id)
        self.repo.delete(show)
        invalidate_show_cache(show_id)
