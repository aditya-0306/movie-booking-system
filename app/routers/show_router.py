from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth_dependency import require_admin
from app.dependencies.pagination_dependency import pagination_params
from app.schemas.common_schema import PaginationParams
from app.schemas.show_schema import ShowCreate, ShowUpdate, ShowOut
from app.schemas.theatre_schema import SeatAvailability
from app.services.show_service import ShowService

router = APIRouter(prefix="/shows", tags=["Shows"])


@router.post("", response_model=ShowOut, status_code=status.HTTP_201_CREATED)
def create_show(payload: ShowCreate, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    return ShowService(db).create_show(payload)


@router.get("")
def list_shows(
    movie_id: Optional[int] = None,
    theatre_id: Optional[int] = None,
    show_date: Optional[date] = None,
    pagination: PaginationParams = Depends(pagination_params),
    db: Session = Depends(get_db),
):
    return ShowService(db).list_shows(pagination, movie_id=movie_id, theatre_id=theatre_id, show_date=show_date)


@router.get("/{show_id}")
def get_show_detail(show_id: int, db: Session = Depends(get_db)):
    return ShowService(db).get_show_detail(show_id)


@router.get("/{show_id}/seats", response_model=list[SeatAvailability])
def get_seat_availability(show_id: int, db: Session = Depends(get_db)):
    return ShowService(db).get_seat_availability(show_id)


@router.put("/{show_id}", response_model=ShowOut)
def update_show(show_id: int, payload: ShowUpdate, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    return ShowService(db).update_show(show_id, payload)


@router.delete("/{show_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_show(show_id: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    ShowService(db).delete_show(show_id)
