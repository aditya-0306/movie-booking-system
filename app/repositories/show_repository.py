from datetime import date, datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.models.show import Show


class ShowRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, show: Show) -> Show:
        self.db.add(show)
        self.db.commit()
        self.db.refresh(show)
        return show

    def get_by_id(self, show_id: int) -> Optional[Show]:
        return self.db.query(Show).filter(Show.id == show_id).first()

    def list(
        self,
        offset: int,
        limit: int,
        movie_id: Optional[int] = None,
        theatre_id: Optional[int] = None,
        show_date: Optional[date] = None,
    ) -> tuple[list[Show], int]:
        query = self.db.query(Show)

        if movie_id:
            query = query.filter(Show.movie_id == movie_id)
        if theatre_id:
            from app.models.theatre import Screen
            query = query.join(Screen, Show.screen_id == Screen.id).filter(Screen.theatre_id == theatre_id)
        if show_date:
            start = datetime.combine(show_date, datetime.min.time())
            end = datetime.combine(show_date, datetime.max.time())
            query = query.filter(Show.show_time >= start, Show.show_time <= end)

        total = query.count()
        items = query.order_by(Show.show_time.asc()).offset(offset).limit(limit).all()
        return items, total

    def update(self, show: Show) -> Show:
        self.db.commit()
        self.db.refresh(show)
        return show

    def delete(self, show: Show) -> None:
        self.db.delete(show)
        self.db.commit()
