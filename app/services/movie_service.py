import math
from typing import Optional
from sqlalchemy.orm import Session

from app.middleware.exception_handler import AppException
from app.models.movie import Movie
from app.repositories.movie_repository import MovieRepository
from app.schemas.movie_schema import MovieCreate, MovieUpdate
from app.schemas.common_schema import PaginatedResponse, PaginationParams
from app.services.cache_service import (
    get_cached, set_cached, invalidate_movie_list_cache, MOVIE_LIST_PREFIX,
)
from app.config import settings


class MovieService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = MovieRepository(db)

    def create_movie(self, data: MovieCreate) -> Movie:
        movie = Movie(**data.model_dump())
        movie = self.repo.create(movie)
        invalidate_movie_list_cache()
        return movie

    def get_movie(self, movie_id: int) -> Movie:
        movie = self.repo.get_by_id(movie_id)
        if not movie:
            raise AppException(404, "Movie not found")
        return movie

    def list_movies(
        self,
        pagination: PaginationParams,
        genre: Optional[str] = None,
        language: Optional[str] = None,
        search: Optional[str] = None,
    ) -> dict:
        # Cache only the common "no filters, page 1" case -- filtered/searched
        # queries are cheap enough on an indexed table that caching every
        # possible filter combination isn't worth the complexity.
        cache_key = None
        if not genre and not language and not search and pagination.page == 1:
            cache_key = f"{MOVIE_LIST_PREFIX}page1:{pagination.page_size}"
            cached = get_cached(cache_key)
            if cached:
                return cached

        items, total = self.repo.list(
            offset=pagination.offset,
            limit=pagination.page_size,
            genre=genre,
            language=language,
            search=search,
        )

        result = {
            "items": [self._to_dict(m) for m in items],
            "total": total,
            "page": pagination.page,
            "page_size": pagination.page_size,
            "total_pages": math.ceil(total / pagination.page_size) if total else 0,
        }

        if cache_key:
            set_cached(cache_key, result, settings.MOVIE_CACHE_TTL_SECONDS)

        return result

    def update_movie(self, movie_id: int, data: MovieUpdate) -> Movie:
        movie = self.get_movie(movie_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(movie, field, value)
        movie = self.repo.update(movie)
        invalidate_movie_list_cache()
        return movie

    def delete_movie(self, movie_id: int) -> None:
        movie = self.get_movie(movie_id)
        self.repo.delete(movie)
        invalidate_movie_list_cache()

    @staticmethod
    def _to_dict(movie: Movie) -> dict:
        return {
            "id": movie.id,
            "title": movie.title,
            "description": movie.description,
            "duration_minutes": movie.duration_minutes,
            "genre": movie.genre,
            "language": movie.language,
            "release_date": movie.release_date,
            "rating": movie.rating,
            "poster_url": movie.poster_url,
            "created_at": movie.created_at,
        }
