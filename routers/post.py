import json
import os
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from auth.jwt import get_current_user, get_current_user_optional
from crud.post import create_post, get_post_by_id, get_posts, get_posts_by_owner
from database_connection import get_db
from schemas.post import PostCreate, PostCreateResponse, PostOut


router = APIRouter(prefix="/posts", tags=["Posts"])

UPLOAD_DIR = "static/uploads/posts"
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}


def _parse_features(features_raw: Optional[str]) -> List[str]:
    if not features_raw:
        return []

    raw = features_raw.strip()
    if not raw:
        return []

    if raw.startswith("["):
        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, list):
                raise ValueError
            return [str(item).strip() for item in parsed if str(item).strip()]
        except (json.JSONDecodeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="features must be a JSON array or comma-separated string",
            )

    return [item.strip() for item in raw.split(",") if item.strip()]


async def _save_images(files: Optional[List[UploadFile]]) -> List[str]:
    if not files:
        return []

    image_urls: List[str] = []

    for file in files:
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported image type: {file.content_type}",
            )

        extension = os.path.splitext(file.filename or "")[1].lower() or ".jpg"
        file_name = f"{uuid.uuid4().hex}{extension}"
        file_path = os.path.join(UPLOAD_DIR, file_name)

        data = await file.read()
        with open(file_path, "wb") as output:
            output.write(data)

        image_urls.append(f"/static/uploads/posts/{file_name}")

    return image_urls


@router.post("", response_model=PostCreateResponse, status_code=status.HTTP_201_CREATED)
async def add_post(
    post_title: str = Form(...),
    price_per_day: float = Form(...),
    location: str = Form(...),
    contact_number: str = Form(...),
    description: str = Form(...),
    features: Optional[str] = Form(None),
    images: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    payload = PostCreate(
        post_title=post_title,
        price_per_day=price_per_day,
        location=location,
        contact_number=contact_number,
        description=description,
        features=_parse_features(features),
        image_urls=await _save_images(images),
    )

    post = create_post(db, owner_id=current_user.id, payload=payload)
    return {
        "message": "Post created successfully.",
        "post": post,
    }


@router.get("", response_model=List[PostOut], status_code=status.HTTP_200_OK)
def list_posts(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    safe_skip = max(skip, 0)
    safe_limit = min(max(limit, 1), 100)
    return get_posts(db, skip=safe_skip, limit=safe_limit)


@router.get("/me", response_model=List[PostOut], status_code=status.HTTP_200_OK)
def list_my_posts(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    safe_skip = max(skip, 0)
    safe_limit = min(max(limit, 1), 100)

    # Backward compatibility for clients that call /posts/me before login.
    if current_user is None:
        return get_posts(db, skip=safe_skip, limit=safe_limit)

    return get_posts_by_owner(db, owner_id=current_user.id, skip=safe_skip, limit=safe_limit)


@router.get("/{post_id}", response_model=PostOut, status_code=status.HTTP_200_OK)
def get_post(post_id: int, db: Session = Depends(get_db)):
    post = get_post_by_id(db, post_id=post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    return post
