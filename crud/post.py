from typing import Optional

from sqlalchemy.orm import Session

from models.booking import Booking
from models.post import Post
from models.review import Review
from schemas.post import PostCreate


def create_post(db: Session, owner_id: int, payload: PostCreate) -> Post:
    db_post = Post(
        owner_id=owner_id,
        post_title=payload.post_title,
        category=payload.category,
        price_per_day=payload.price_per_day,
        location=payload.location,
        contact_number=payload.contact_number,
        description=payload.description,
        features=payload.features,
        image_urls=payload.image_urls,
    )
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post


def get_posts(db: Session, skip: int = 0, limit: int = 20, category: Optional[str] = None) -> list[Post]:
    query = db.query(Post)
    normalized_category = (category or "").strip().lower()
    if normalized_category and normalized_category != "all":
        query = query.filter(Post.category == normalized_category)

    return (
        query
        .order_by(Post.created_at.desc(), Post.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

def get_post_by_id(db: Session, post_id: int) -> Optional[Post]:
    return db.query(Post).filter(Post.id == post_id).first()


def get_posts_by_owner(
    db: Session,
    owner_id: int,
    skip: int = 0,
    limit: int = 20,
    category: Optional[str] = None,
) -> list[Post]:
    query = db.query(Post).filter(Post.owner_id == owner_id)
    normalized_category = (category or "").strip().lower()
    if normalized_category and normalized_category != "all":
        query = query.filter(Post.category == normalized_category)

    return (
        query
        .order_by(Post.created_at.desc(), Post.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_post(
    db: Session,
    post_id: int,
    owner_id: int,
    payload: PostCreate,
    is_admin: bool = False,
) -> Optional[Post]:
    if is_admin:
        db_post = db.query(Post).filter(Post.id == post_id).first()
    else:
        db_post = db.query(Post).filter(Post.id == post_id, Post.owner_id == owner_id).first()
    if not db_post:
        return None
    db_post.post_title = payload.post_title
    db_post.category = payload.category
    db_post.price_per_day = payload.price_per_day
    db_post.location = payload.location
    db_post.contact_number = payload.contact_number
    db_post.description = payload.description
    db_post.features = payload.features
    db_post.image_urls = payload.image_urls
    db.commit()
    db.refresh(db_post)
    return db_post


def delete_post(db: Session, post_id: int, owner_id: int, is_admin: bool = False) -> bool:
    if is_admin:
        db_post = db.query(Post).filter(Post.id == post_id).first()
    else:
        db_post = db.query(Post).filter(Post.id == post_id, Post.owner_id == owner_id).first()
    if not db_post:
        return False

    db.query(Review).filter(Review.post_id == post_id).delete(synchronize_session=False)
    db.query(Booking).filter(Booking.post_id == post_id).delete(synchronize_session=False)
    db.delete(db_post)
    db.commit()
    return True
