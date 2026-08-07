from typing import Optional
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.movie import Movie


class MovieRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, movie: Movie) -> Movie:
        self.db.add(movie)
        self.db.commit()
        self.db.refresh(movie)
        return movie

    def get_by_id(self, movie_id: int) -> Optional[Movie]:
        return self.db.query(Movie).filter(Movie.id == movie_id).first()

    def list(
        self,
        offset: int,
        limit: int,
        genre: Optional[str] = None,
        language: Optional[str] = None,
        search: Optional[str] = None,
    ) -> tuple[list[Movie], int]:
        query = self.db.query(Movie)

        if genre:
            query = query.filter(Movie.genre.ilike(f"%{genre}%"))
        if language:
            query = query.filter(Movie.language.ilike(f"%{language}%"))
        if search:
            query = query.filter(
                or_(Movie.title.ilike(f"%{search}%"), Movie.description.ilike(f"%{search}%"))
            )

        total = query.count()
        items = query.order_by(Movie.id.desc()).offset(offset).limit(limit).all()
        return items, total

    def update(self, movie: Movie) -> Movie:
        self.db.commit()
        self.db.refresh(movie)
        return movie

    def delete(self, movie: Movie) -> None:
        self.db.delete(movie)
        self.db.commit()
