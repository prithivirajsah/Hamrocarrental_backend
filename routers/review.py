from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth.jwt import get_current_user
from crud.booking import has_user_booking_for_post
from crud.post import get_post_by_id
from crud.review import (
    create_review,
    delete_review,
    get_review_by_id,
    get_reviews,
    get_reviews_by_post,
    get_reviews_by_user,
    has_user_review_for_post,
    update_review,
    update_review_likes,
)
from crud.user import get_user_by_id
from database_connection import get_db
from schemas.review import ReviewCreate, ReviewCreateResponse, ReviewLikeUpdate, ReviewOut, ReviewUpdate


router = APIRouter(prefix="/reviews", tags=["Reviews"])


def _to_review_out(db: Session, review) -> ReviewOut:
    renter = get_user_by_id(db, review.user_id)
    post = get_post_by_id(db, review.post_id)

    return ReviewOut(
        id=review.id,
        post_id=review.post_id,
        user_id=review.user_id,
        rating=review.rating,
        content=review.content,
        likes=review.likes,
        created_at=review.created_at,
        updated_at=review.updated_at,
        user_name=getattr(renter, "full_name", None),
        role="Verified Renter",
        vehicle_name=getattr(post, "post_title", None),
    )


@router.post("", response_model=ReviewCreateResponse, status_code=status.HTTP_201_CREATED)
def add_review(
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    post = get_post_by_id(db, payload.post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle post not found",
        )

    if not has_user_booking_for_post(db, user_id=current_user.id, post_id=payload.post_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can review this vehicle only after booking it",
        )

    if has_user_review_for_post(db, user_id=current_user.id, post_id=payload.post_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already submitted a review for this vehicle",
        )

    review = create_review(db, user_id=current_user.id, payload=payload)
    return {
        "message": "Review submitted successfully.",
        "review": _to_review_out(db, review),
    }


@router.get("", response_model=List[ReviewOut], status_code=status.HTTP_200_OK)
def list_reviews(
    skip: int = 0,
    limit: int = 50,
    post_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    safe_skip = max(skip, 0)
    safe_limit = min(max(limit, 1), 100)

    if post_id:
        records = get_reviews_by_post(db, post_id=post_id, skip=safe_skip, limit=safe_limit)
    else:
        records = get_reviews(db, skip=safe_skip, limit=safe_limit)

    return [_to_review_out(db, review) for review in records]


@router.get("/me", response_model=List[ReviewOut], status_code=status.HTTP_200_OK)
def list_my_reviews(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    safe_skip = max(skip, 0)
    safe_limit = min(max(limit, 1), 100)

    records = get_reviews_by_user(db, user_id=current_user.id, skip=safe_skip, limit=safe_limit)
    return [_to_review_out(db, review) for review in records]


@router.patch("/{review_id}", response_model=ReviewOut, status_code=status.HTTP_200_OK)
def edit_review(
    review_id: int,
    payload: ReviewUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    review = get_review_by_id(db, review_id=review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    if review.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own review",
        )

    updated = update_review(db, review=review, payload=payload)
    return _to_review_out(db, updated)


@router.patch("/{review_id}/likes", response_model=ReviewOut, status_code=status.HTTP_200_OK)
def edit_review_likes(
    review_id: int,
    payload: ReviewLikeUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    review = get_review_by_id(db, review_id=review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    updated = update_review_likes(db, review=review, delta=payload.delta)
    return _to_review_out(db, updated)


@router.delete("/{review_id}", status_code=status.HTTP_200_OK)
def remove_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    review = get_review_by_id(db, review_id=review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    if review.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own review",
        )

    delete_review(db, review)
    return {"message": "Review deleted successfully."}