from typing import Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth_dependency import require_admin
from app.dependencies.pagination_dependency import pagination_params
from app.schemas.common_schema import PaginationParams
from app.schemas.movie_schema import MovieCreate, MovieUpdate, MovieOut
from app.services.movie_service import MovieService

router = APIRouter(prefix="/movies", tags=["Movies"])


@router.post("", response_model=MovieOut, status_code=status.HTTP_201_CREATED)
def create_movie(payload: MovieCreate, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    return MovieService(db).create_movie(payload)


@router.get("")
def list_movies(
    genre: Optional[str] = None,
    language: Optional[str] = None,
    search: Optional[str] = None,
    pagination: PaginationParams = Depends(pagination_params),
    db: Session = Depends(get_db),
):
    return MovieService(db).list_movies(pagination, genre=genre, language=language, search=search)


@router.get("/{movie_id}", response_model=MovieOut)
def get_movie(movie_id: int, db: Session = Depends(get_db)):
    return MovieService(db).get_movie(movie_id)


@router.put("/{movie_id}", response_model=MovieOut)
def update_movie(movie_id: int, payload: MovieUpdate, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    return MovieService(db).update_movie(movie_id, payload)


@router.delete("/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_movie(movie_id: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    MovieService(db).delete_movie(movie_id)
