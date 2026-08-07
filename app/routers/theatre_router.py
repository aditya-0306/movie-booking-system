from typing import Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth_dependency import require_admin
from app.schemas.theatre_schema import (
    TheatreCreate, TheatreUpdate, TheatreOut,
    ScreenCreate, ScreenOut,
    SeatCreate, SeatGenerateRequest, SeatOut,
)
from app.services.theatre_service import TheatreService

router = APIRouter(tags=["Theatres"])


@router.post("/theatres", response_model=TheatreOut, status_code=status.HTTP_201_CREATED)
def create_theatre(payload: TheatreCreate, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    return TheatreService(db).create_theatre(payload)


@router.get("/theatres/{theatre_id}", response_model=TheatreOut)
def get_theatre(theatre_id: int, db: Session = Depends(get_db)):
    return TheatreService(db).get_theatre(theatre_id)


@router.get("/theatres")
def list_theatres(
    city: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
):
    items, total = TheatreService(db).list_theatres((page - 1) * page_size, page_size, city)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.put("/theatres/{theatre_id}", response_model=TheatreOut)
def update_theatre(
    theatre_id: int, payload: TheatreUpdate, db: Session = Depends(get_db), _admin=Depends(require_admin)
):
    return TheatreService(db).update_theatre(theatre_id, payload)


@router.delete("/theatres/{theatre_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_theatre(theatre_id: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    TheatreService(db).delete_theatre(theatre_id)


@router.post("/screens", response_model=ScreenOut, status_code=status.HTTP_201_CREATED)
def create_screen(payload: ScreenCreate, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    return TheatreService(db).create_screen(payload)


@router.get("/theatres/{theatre_id}/screens", response_model=list[ScreenOut])
def list_screens(theatre_id: int, db: Session = Depends(get_db)):
    return TheatreService(db).list_screens(theatre_id)


@router.delete("/screens/{screen_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_screen(screen_id: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    TheatreService(db).delete_screen(screen_id)


@router.post("/screens/{screen_id}/seats", response_model=SeatOut, status_code=status.HTTP_201_CREATED)
def add_seat(screen_id: int, payload: SeatCreate, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    return TheatreService(db).add_seat(screen_id, payload)


@router.post("/screens/{screen_id}/seats/generate", response_model=list[SeatOut], status_code=status.HTTP_201_CREATED)
def generate_seats(
    screen_id: int, payload: SeatGenerateRequest, db: Session = Depends(get_db), _admin=Depends(require_admin)
):
    """Convenience bulk endpoint -- e.g. {rows: 8, seats_per_row: 12, premium_rows: 2}
    creates 96 seats in one call instead of 96 individual POST requests."""
    return TheatreService(db).generate_seats(screen_id, payload)


@router.get("/screens/{screen_id}/seats", response_model=list[SeatOut])
def list_seats(screen_id: int, db: Session = Depends(get_db)):
    return TheatreService(db).list_seats(screen_id)
