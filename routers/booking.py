from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth.jwt import get_current_user
from crud.booking import (
    create_booking,
    get_booking_by_id,
    get_bookings,
    get_bookings_by_owner,
    get_bookings_by_user,
    has_booking_overlap,
    update_booking_status,
)
from crud.post import get_post_by_id
from crud.user import get_user_by_id
from database_connection import get_db
from schemas.booking import (
    BookingAvailabilityResponse,
    BookingCreate,
    BookingCreateResponse,
    BookingOut,
    BookingStatusUpdate,
)


router = APIRouter(prefix="/bookings", tags=["Bookings"])


def _to_booking_out(db: Session, booking) -> BookingOut:
    renter = get_user_by_id(db, booking.user_id)
    post = get_post_by_id(db, booking.post_id)

    return BookingOut(
        id=booking.id,
        post_id=booking.post_id,
        user_id=booking.user_id,
        owner_id=booking.owner_id,
        pickup_location=booking.pickup_location,
        return_location=booking.return_location,
        start_date=booking.start_date,
        end_date=booking.end_date,
        total_days=booking.total_days,
        price_per_day=booking.price_per_day,
        total_price=booking.total_price,
        status=booking.status,
        note=booking.note,
        created_at=booking.created_at,
        user_name=getattr(renter, "full_name", None),
        user_email=getattr(renter, "email", None),
        vehicle_name=getattr(post, "post_title", None),
    )


@router.post("", response_model=BookingCreateResponse, status_code=status.HTTP_201_CREATED)
def add_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    post = get_post_by_id(db, payload.post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle post not found",
        )

    if post.owner_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot book your own vehicle",
        )

    if payload.start_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date cannot be in the past",
        )

    total_days = (payload.end_date - payload.start_date).days + 1
    if total_days <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date range",
        )

    if has_booking_overlap(
        db,
        post_id=post.id,
        start_date=payload.start_date,
        end_date=payload.end_date,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Selected date range is not available for this vehicle",
        )

    total_price = float(post.price_per_day) * total_days

    booking = create_booking(
        db=db,
        post_id=post.id,
        user_id=current_user.id,
        owner_id=post.owner_id,
        pickup_location=payload.pickup_location,
        return_location=payload.return_location,
        start_date=payload.start_date,
        end_date=payload.end_date,
        total_days=total_days,
        price_per_day=float(post.price_per_day),
        total_price=total_price,
        note=payload.note,
    )

    return {
        "message": "Booking created successfully.",
        "booking": _to_booking_out(db, booking),
    }


@router.get("", response_model=List[BookingOut], status_code=status.HTTP_200_OK)
def list_bookings(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    safe_skip = max(skip, 0)
    safe_limit = min(max(limit, 1), 100)

    if current_user.role == "admin":
        records = get_bookings(db, skip=safe_skip, limit=safe_limit)
    else:
        records = get_bookings_by_user(db, user_id=current_user.id, skip=safe_skip, limit=safe_limit)

    return [_to_booking_out(db, booking) for booking in records]


@router.get("/me", response_model=List[BookingOut], status_code=status.HTTP_200_OK)
def list_my_bookings(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    safe_skip = max(skip, 0)
    safe_limit = min(max(limit, 1), 100)
    records = get_bookings_by_user(db, user_id=current_user.id, skip=safe_skip, limit=safe_limit)
    return [_to_booking_out(db, booking) for booking in records]


@router.get("/owner/me", response_model=List[BookingOut], status_code=status.HTTP_200_OK)
def list_owner_bookings(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    safe_skip = max(skip, 0)
    safe_limit = min(max(limit, 1), 100)
    records = get_bookings_by_owner(db, owner_id=current_user.id, skip=safe_skip, limit=safe_limit)
    return [_to_booking_out(db, booking) for booking in records]


@router.get("/availability", response_model=BookingAvailabilityResponse, status_code=status.HTTP_200_OK)
def check_booking_availability(
    post_id: int,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
):
    post = get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle post not found",
        )

    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be greater than or equal to start date",
        )

    available = not has_booking_overlap(
        db,
        post_id=post_id,
        start_date=start_date,
        end_date=end_date,
    )
    return {
        "post_id": post_id,
        "start_date": start_date,
        "end_date": end_date,
        "available": available,
    }


@router.patch("/{booking_id}/status", response_model=BookingOut, status_code=status.HTTP_200_OK)
def change_booking_status(
    booking_id: int,
    payload: BookingStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update booking status",
        )

    booking = get_booking_by_id(db, booking_id=booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    updated = update_booking_status(db, booking=booking, status=payload.status.value)
    return _to_booking_out(db, updated)
