from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from auth.jwt import get_current_user
from crud.booking import (
    check_booking_overlap,
    create_booking,
    get_all_bookings,
    get_booking_by_id,
    get_bookings_by_user,
    update_booking_status,
)
from database_connection import get_db
from schemas.booking import BookingCreate, BookingOut, BookingStatusUpdate

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.get("/meta")
def booking_meta():
    return {
        "vehicle_types": ["Hatchback", "Sedan", "SUV", "Pickup", "Van", "Luxury"],
        "locations": ["Kathmandu", "Pokhara", "Lalitpur", "Bhaktapur", "Butwal", "Chitwan"],
    }


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_booking_endpoint(
    booking_in: BookingCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if check_booking_overlap(
        db,
        vehicle_type=booking_in.vehicle_type,
        pickup_location=booking_in.pickup_location,
        pickup_date=booking_in.pickup_date,
        return_date=booking_in.return_date,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Selected vehicle type is not available for those dates at this location",
        )

    booking = create_booking(db, current_user.id, booking_in)
    return booking


@router.get("/me", response_model=List[BookingOut])
def my_bookings(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return get_bookings_by_user(db, user_id=current_user.id, skip=skip, limit=limit)


@router.get("", response_model=List[BookingOut])
def all_bookings(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view all bookings",
        )
    return get_all_bookings(db, skip=skip, limit=limit)


@router.get("/{booking_id}", response_model=BookingOut)
def get_booking_detail(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    booking = get_booking_by_id(db, booking_id)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    if current_user.role != "admin" and booking.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return booking


@router.patch("/{booking_id}/status", response_model=BookingOut)
def update_booking_status_endpoint(
    booking_id: int,
    payload: BookingStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    booking = get_booking_by_id(db, booking_id)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update booking status",
        )

    return update_booking_status(db, booking, payload.status.value)
