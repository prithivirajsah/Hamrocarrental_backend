from datetime import date
from typing import List, Optional
from sqlalchemy.orm import Session

from models.booking import Booking
from schemas.booking import BookingCreate


def create_booking(db: Session, user_id: int, booking_in: BookingCreate) -> Booking:
    booking = Booking(
        user_id=user_id,
        vehicle_type=booking_in.vehicle_type,
        pickup_location=booking_in.pickup_location,
        dropoff_location=booking_in.dropoff_location,
        pickup_date=booking_in.pickup_date,
        return_date=booking_in.return_date,
        status="pending",
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def get_booking_by_id(db: Session, booking_id: int) -> Optional[Booking]:
    return db.query(Booking).filter(Booking.id == booking_id).first()


def get_bookings_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Booking]:
    return (
        db.query(Booking)
        .filter(Booking.user_id == user_id)
        .order_by(Booking.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_all_bookings(db: Session, skip: int = 0, limit: int = 100) -> List[Booking]:
    return (
        db.query(Booking)
        .order_by(Booking.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_booking_status(db: Session, booking: Booking, status: str) -> Booking:
    booking.status = status
    db.commit()
    db.refresh(booking)
    return booking


def check_booking_overlap(
    db: Session,
    vehicle_type: str,
    pickup_location: str,
    pickup_date: date,
    return_date: date,
) -> bool:
    # Basic overlap rule: same vehicle type + location cannot be double-booked on overlapping dates.
    overlapping = (
        db.query(Booking)
        .filter(Booking.vehicle_type == vehicle_type)
        .filter(Booking.pickup_location == pickup_location)
        .filter(Booking.status.in_(["pending", "confirmed"]))
        .filter(Booking.pickup_date <= return_date)
        .filter(Booking.return_date >= pickup_date)
        .first()
    )
    return overlapping is not None
