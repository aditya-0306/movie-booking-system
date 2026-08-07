from typing import Optional
from sqlalchemy.orm import Session

from app.middleware.exception_handler import AppException
from app.models.theatre import Theatre, Screen, Seat
from app.repositories.theatre_repository import TheatreRepository
from app.schemas.theatre_schema import (
    TheatreCreate, TheatreUpdate, ScreenCreate, SeatCreate, SeatGenerateRequest,
)


class TheatreService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = TheatreRepository(db)

    # ---- Theatres ----
    def create_theatre(self, data: TheatreCreate) -> Theatre:
        return self.repo.create_theatre(Theatre(**data.model_dump()))

    def get_theatre(self, theatre_id: int) -> Theatre:
        theatre = self.repo.get_theatre(theatre_id)
        if not theatre:
            raise AppException(404, "Theatre not found")
        return theatre

    def list_theatres(self, offset: int, limit: int, city: Optional[str] = None):
        return self.repo.list_theatres(offset, limit, city)

    def update_theatre(self, theatre_id: int, data: TheatreUpdate) -> Theatre:
        theatre = self.get_theatre(theatre_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(theatre, field, value)
        return self.repo.update_theatre(theatre)

    def delete_theatre(self, theatre_id: int) -> None:
        theatre = self.get_theatre(theatre_id)
        self.repo.delete_theatre(theatre)

    # ---- Screens ----
    def create_screen(self, data: ScreenCreate) -> Screen:
        self.get_theatre(data.theatre_id)  # 404s if theatre doesn't exist
        return self.repo.create_screen(Screen(theatre_id=data.theatre_id, name=data.name))

    def get_screen(self, screen_id: int) -> Screen:
        screen = self.repo.get_screen(screen_id)
        if not screen:
            raise AppException(404, "Screen not found")
        return screen

    def list_screens(self, theatre_id: int) -> list[Screen]:
        self.get_theatre(theatre_id)
        return self.repo.list_screens_for_theatre(theatre_id)

    def delete_screen(self, screen_id: int) -> None:
        screen = self.get_screen(screen_id)
        self.repo.delete_screen(screen)

    # ---- Seats ----
    def add_seat(self, screen_id: int, data: SeatCreate) -> Seat:
        self.get_screen(screen_id)
        seat = Seat(screen_id=screen_id, seat_number=data.seat_number, seat_type=data.seat_type)
        seats = self.repo.create_seats_bulk([seat])
        self._refresh_seat_count(screen_id)
        return seats[0]

    def generate_seats(self, screen_id: int, data: SeatGenerateRequest) -> list[Seat]:
        """Convenience bulk-generator: e.g. 10 rows x 12 seats/row -> A1..A12, B1..B12, ..."""
        screen = self.get_screen(screen_id)
        seats = []
        for row_index in range(data.rows):
            row_letter = chr(ord("A") + row_index)
            seat_type = "premium" if row_index < data.premium_rows else "regular"
            for seat_num in range(1, data.seats_per_row + 1):
                seats.append(
                    Seat(screen_id=screen_id, seat_number=f"{row_letter}{seat_num}", seat_type=seat_type)
                )
        created = self.repo.create_seats_bulk(seats)
        self._refresh_seat_count(screen_id)
        return created

    def list_seats(self, screen_id: int) -> list[Seat]:
        self.get_screen(screen_id)
        return self.repo.list_seats_for_screen(screen_id)

    def _refresh_seat_count(self, screen_id: int) -> None:
        screen = self.repo.get_screen(screen_id)
        screen.total_seats = len(self.repo.list_seats_for_screen(screen_id))
        self.db.commit()
