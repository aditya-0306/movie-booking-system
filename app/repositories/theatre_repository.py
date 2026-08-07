from typing import Optional
from sqlalchemy.orm import Session

from app.models.theatre import Theatre, Screen, Seat


class TheatreRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_theatre(self, theatre: Theatre) -> Theatre:
        self.db.add(theatre)
        self.db.commit()
        self.db.refresh(theatre)
        return theatre

    def get_theatre(self, theatre_id: int) -> Optional[Theatre]:
        return self.db.query(Theatre).filter(Theatre.id == theatre_id).first()

    def list_theatres(self, offset: int, limit: int, city: Optional[str] = None) -> tuple[list[Theatre], int]:
        query = self.db.query(Theatre)
        if city:
            query = query.filter(Theatre.city.ilike(f"%{city}%"))
        total = query.count()
        items = query.order_by(Theatre.id.desc()).offset(offset).limit(limit).all()
        return items, total

    def update_theatre(self, theatre: Theatre) -> Theatre:
        self.db.commit()
        self.db.refresh(theatre)
        return theatre

    def delete_theatre(self, theatre: Theatre) -> None:
        self.db.delete(theatre)
        self.db.commit()

    def create_screen(self, screen: Screen) -> Screen:
        self.db.add(screen)
        self.db.commit()
        self.db.refresh(screen)
        return screen

    def get_screen(self, screen_id: int) -> Optional[Screen]:
        return self.db.query(Screen).filter(Screen.id == screen_id).first()

    def list_screens_for_theatre(self, theatre_id: int) -> list[Screen]:
        return self.db.query(Screen).filter(Screen.theatre_id == theatre_id).all()

    def delete_screen(self, screen: Screen) -> None:
        self.db.delete(screen)
        self.db.commit()

    def create_seats_bulk(self, seats: list[Seat]) -> list[Seat]:
        self.db.add_all(seats)
        self.db.commit()
        for s in seats:
            self.db.refresh(s)
        return seats

    def list_seats_for_screen(self, screen_id: int) -> list[Seat]:
        return self.db.query(Seat).filter(Seat.screen_id == screen_id).all()

    def get_seat(self, seat_id: int) -> Optional[Seat]:
        return self.db.query(Seat).filter(Seat.id == seat_id).first()
