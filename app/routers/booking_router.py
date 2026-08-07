from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.pagination_dependency import pagination_params
from app.models.user import User
from app.schemas.booking_schema import BookingCreate, BookingBatchResult, BookingOut
from app.schemas.common_schema import PaginationParams
from app.services.auth_service import get_current_user
from app.services.booking_service import BookingService

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("", response_model=BookingBatchResult, status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Books one or more seats for a show. This is the concurrency-critical
    endpoint: if two users request the same seat at the same instant, the
    database's partial unique index guarantees exactly one of them succeeds
    and the other gets a clean 409 -- see BookingRepository.try_reserve_seats
    for the full explanation.
    """
    return BookingService(db).create_booking(current_user, payload)


@router.get("/me")
def list_my_bookings(
    pagination: PaginationParams = Depends(pagination_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return BookingService(db).list_my_bookings(current_user, pagination)


@router.get("/{booking_id}", response_model=BookingOut)
def get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return BookingService(db).get_booking(booking_id)


@router.post("/{booking_id}/cancel", response_model=BookingOut)
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return BookingService(db).cancel_booking(current_user, booking_id)
