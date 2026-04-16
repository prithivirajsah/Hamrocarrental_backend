from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.booking import Booking
from models.post import Post
from models.review import Review
from schemas.review import ReviewCreate, ReviewUpdate


def create_review(db: Session, user_id: int, payload: ReviewCreate) -> Review:
    db_review = Review(
        post_id=payload.post_id,
        user_id=user_id,
        rating=payload.rating,
        content=payload.content,
        likes=0,
    )
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review


def get_review_by_id(db: Session, review_id: int) -> Optional[Review]:
    return db.query(Review).filter(Review.id == review_id).first()


def get_reviews(db: Session, skip: int = 0, limit: int = 50) -> list[Review]:
    return (
        db.query(Review)
        .filter(Review.driver_id.is_(None))
        .order_by(Review.created_at.desc(), Review.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_reviews_by_post(db: Session, post_id: int, skip: int = 0, limit: int = 50) -> list[Review]:
    return (
        db.query(Review)
        .filter(Review.post_id == post_id, Review.driver_id.is_(None))
        .order_by(Review.created_at.desc(), Review.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_reviews_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 50) -> list[Review]:
    return (
        db.query(Review)
        .filter(Review.user_id == user_id, Review.driver_id.is_(None))
        .order_by(Review.created_at.desc(), Review.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def has_user_review_for_post(db: Session, user_id: int, post_id: int) -> bool:
    return (
        db.query(Review)
        .filter(Review.user_id == user_id, Review.post_id == post_id, Review.driver_id.is_(None))
        .first()
        is not None
    )


def create_driver_review(
    db: Session,
    user_id: int,
    booking_id: int,
    post_id: int,
    driver_id: int,
    rating: int,
    content: str,
) -> Review:
    db_review = Review(
        post_id=post_id,
        user_id=user_id,
        booking_id=booking_id,
        driver_id=driver_id,
        rating=rating,
        content=content,
        likes=0,
    )
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review


def has_user_review_for_driver_booking(db: Session, user_id: int, booking_id: int, driver_id: int) -> bool:
    return (
        db.query(Review)
        .filter(
            Review.user_id == user_id,
            Review.booking_id == booking_id,
            Review.driver_id == driver_id,
        )
        .first()
        is not None
    )


def get_driver_reviews(db: Session, driver_id: int, skip: int = 0, limit: int = 50) -> list[Review]:
    return (
        db.query(Review)
        .filter(Review.driver_id == driver_id)
        .order_by(Review.created_at.desc(), Review.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_driver_review_summary(db: Session, driver_id: int) -> dict:
    total_reviews = (
        db.query(func.count(Review.id))
        .filter(Review.driver_id == driver_id)
        .scalar()
        or 0
    )

    avg_rating_value = (
        db.query(func.avg(Review.rating))
        .filter(Review.driver_id == driver_id)
        .scalar()
    )

    average_rating = float(avg_rating_value) if avg_rating_value is not None else 0.0

    return {
        "driver_id": driver_id,
        "total_reviews": int(total_reviews),
        "average_rating": round(average_rating, 2),
    }


def update_review(db: Session, review: Review, payload: ReviewUpdate) -> Review:
    if payload.rating is not None:
        review.rating = payload.rating
    if payload.content is not None:
        review.content = payload.content

    db.commit()
    db.refresh(review)
    return review


def update_review_likes(db: Session, review: Review, delta: int) -> Review:
    review.likes = max(0, int(review.likes or 0) + delta)
    db.commit()
    db.refresh(review)
    return review


def delete_review(db: Session, review: Review) -> None:
    db.delete(review)
    db.commit()


def get_review_reminders_for_user(db: Session, user_id: int, skip: int = 0, limit: int = 50) -> list[dict]:
    completed_bookings = (
        db.query(Booking, Post)
        .join(Post, Booking.post_id == Post.id)
        .outerjoin(
            Review,
            (Review.post_id == Booking.post_id)
            & (Review.user_id == Booking.user_id)
            & (Review.driver_id.is_(None)),
        )
        .filter(
            Booking.user_id == user_id,
            Booking.status == "completed",
            Review.id.is_(None),
        )
        .order_by(Booking.created_at.desc(), Booking.id.desc())
        .all()
    )

    reminders: list[dict] = []
    seen_post_ids: set[int] = set()

    for booking, post in completed_bookings:
        if booking.post_id in seen_post_ids:
            continue
        seen_post_ids.add(booking.post_id)
        reminders.append(
            {
                "booking_id": booking.id,
                "post_id": booking.post_id,
                "vehicle_name": getattr(post, "post_title", None),
                "owner_id": booking.owner_id,
                "start_date": booking.start_date,
                "end_date": booking.end_date,
                "completed_at": booking.created_at,
                "message": "Your rental is completed. Please leave a review.",
            }
        )

    return reminders[skip : skip + limit]