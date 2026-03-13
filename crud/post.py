from typing import Optional

from sqlalchemy.orm import Session

from models.post import Post
from schemas.post import PostCreate


def create_post(db: Session, owner_id: int, payload: PostCreate) -> Post:
    db_post = Post(
        owner_id=owner_id,
        post_title=payload.post_title,
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


def get_posts(db: Session, skip: int = 0, limit: int = 20) -> list[Post]:
    return (
        db.query(Post)
        .order_by(Post.created_at.desc(), Post.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

def get_post_by_id(db: Session, post_id: int) -> Optional[Post]:
    return db.query(Post).filter(Post.id == post_id).first()


def get_posts_by_owner(db: Session, owner_id: int, skip: int = 0, limit: int = 20) -> list[Post]:
    return (
        db.query(Post)
        .filter(Post.owner_id == owner_id)
        .order_by(Post.created_at.desc(), Post.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_post(db: Session, post_id: int, owner_id: int, payload: PostCreate) -> Optional[Post]:
    db_post = db.query(Post).filter(Post.id == post_id, Post.owner_id == owner_id).first()
    if not db_post:
        return None
    db_post.post_title = payload.post_title
    db_post.price_per_day = payload.price_per_day
    db_post.location = payload.location
    db_post.contact_number = payload.contact_number
    db_post.description = payload.description
    db_post.features = payload.features
    db_post.image_urls = payload.image_urls
    db.commit()
    db.refresh(db_post)
    return db_post


def delete_post(db: Session, post_id: int, owner_id: int) -> bool:
    db_post = db.query(Post).filter(Post.id == post_id, Post.owner_id == owner_id).first()
    if not db_post:
        return False
    db.delete(db_post)
    db.commit()
    return True
