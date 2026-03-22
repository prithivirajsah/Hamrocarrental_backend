from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from models.booking import Booking


def create_booking(
    db: Session,
    post_id: int,
    user_id: int,
    owner_id: int,
    pickup_location: str,
    return_location: str,
    start_date,
    end_date,
    total_days: int,
    price_per_day: float,
    total_price: float,
    note: Optional[str] = None,
) -> Booking:
    booking = Booking(
        post_id=post_id,
        user_id=user_id,
        owner_id=owner_id,
        pickup_location=pickup_location,
        return_location=return_location,
        start_date=start_date,
        end_date=end_date,
        total_days=total_days,
        price_per_day=price_per_day,
        total_price=total_price,
        status="pending",
        note=note,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def get_booking_by_id(db: Session, booking_id: int) -> Optional[Booking]:
    return db.query(Booking).filter(Booking.id == booking_id).first()


def get_bookings(db: Session, skip: int = 0, limit: int = 50) -> list[Booking]:
    return (
        db.query(Booking)
        .filter(Booking.post_id.isnot(None))
        .order_by(Booking.created_at.desc(), Booking.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_bookings_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 50) -> list[Booking]:
    return (
        db.query(Booking)
        .filter(Booking.user_id == user_id, Booking.post_id.isnot(None))
        .order_by(Booking.created_at.desc(), Booking.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_bookings_by_owner(db: Session, owner_id: int, skip: int = 0, limit: int = 50) -> list[Booking]:
    return (
        db.query(Booking)
        .filter(Booking.owner_id == owner_id, Booking.post_id.isnot(None))
        .order_by(Booking.created_at.desc(), Booking.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def has_user_booking_for_post(db: Session, user_id: int, post_id: int) -> bool:
    return (
        db.query(Booking)
        .filter(
            Booking.user_id == user_id,
            Booking.post_id == post_id,
            Booking.status.in_(["pending", "confirmed", "completed"]),
        )
        .first()
        is not None
    )


def get_existing_user_booking_for_range(
    db: Session,
    user_id: int,
    post_id: int,
    start_date: date,
    end_date: date,
) -> Optional[Booking]:
    return (
        db.query(Booking)
        .filter(
            Booking.user_id == user_id,
            Booking.post_id == post_id,
            Booking.start_date == start_date,
            Booking.end_date == end_date,
            Booking.status.in_(["pending", "confirmed", "completed"]),
        )
        .order_by(Booking.created_at.desc(), Booking.id.desc())
        .first()
    )


def get_existing_user_overlapping_booking_for_post_range(
    db: Session,
    user_id: int,
    post_id: int,
    start_date: date,
    end_date: date,
) -> Optional[Booking]:
    return (
        db.query(Booking)
        .filter(
            Booking.user_id == user_id,
            Booking.post_id == post_id,
            Booking.status.in_(["pending", "confirmed", "completed"]),
            Booking.start_date <= end_date,
            Booking.end_date >= start_date,
        )
        .order_by(Booking.created_at.desc(), Booking.id.desc())
        .first()
    )


def has_booking_overlap_with_other_users(
    db: Session,
    post_id: int,
    start_date: date,
    end_date: date,
    user_id: int,
) -> bool:
    return (
        db.query(Booking)
        .filter(
            Booking.post_id == post_id,
            Booking.user_id != user_id,
            Booking.status.in_(["pending", "confirmed"]),
            Booking.start_date <= end_date,
            Booking.end_date >= start_date,
        )
        .first()
        is not None
    )


def has_booking_overlap(
    db: Session,
    post_id: int,
    start_date: date,
    end_date: date,
) -> bool:
    """Return True if any active/pending booking overlaps the requested range."""
    return (
        db.query(Booking)
        .filter(
            Booking.post_id == post_id,
            Booking.status.in_(["pending", "confirmed"]),
            Booking.start_date <= end_date,
            Booking.end_date >= start_date,
        )
        .first()
        is not None
    )


def update_booking_status(db: Session, booking: Booking, status: str) -> Booking:
    booking.status = status
    db.commit()
    db.refresh(booking)
    return booking
