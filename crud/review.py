from typing import Optional

from sqlalchemy.orm import Session

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
        .order_by(Review.created_at.desc(), Review.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_reviews_by_post(db: Session, post_id: int, skip: int = 0, limit: int = 50) -> list[Review]:
    return (
        db.query(Review)
        .filter(Review.post_id == post_id)
        .order_by(Review.created_at.desc(), Review.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_reviews_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 50) -> list[Review]:
    return (
        db.query(Review)
        .filter(Review.user_id == user_id)
        .order_by(Review.created_at.desc(), Review.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def has_user_review_for_post(db: Session, user_id: int, post_id: int) -> bool:
    return (
        db.query(Review)
        .filter(Review.user_id == user_id, Review.post_id == post_id)
        .first()
        is not None
    )


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