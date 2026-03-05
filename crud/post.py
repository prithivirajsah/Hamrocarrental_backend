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
