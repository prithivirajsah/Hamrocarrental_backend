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


def update_booking_status(db: Session, booking: Booking, status: str) -> Booking:
    booking.status = status
    db.commit()
    db.refresh(booking)
    return booking
