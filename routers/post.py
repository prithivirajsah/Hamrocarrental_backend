import json
import os
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile as StarletteUploadFile

from auth.jwt import get_current_user, get_current_user_optional
from crud.post import create_post, get_post_by_id, get_posts, get_posts_by_owner, update_post, delete_post
from database_connection import get_db
from schemas.post import PostCreate, PostCreateResponse, PostOut


router = APIRouter(prefix="/posts", tags=["Posts"])

UPLOAD_DIR = "static/uploads/posts"
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
POST_CATEGORIES = [
    {"id": "all", "label": "All vehicles", "icon": "🚗"},
    {"id": "sedan", "label": "Sedan", "icon": "🚙"},
    {"id": "cabriolet", "label": "Cabriolet", "icon": "🏎️"},
    {"id": "pickup", "label": "Pickup", "icon": "🛻"},
    {"id": "suv", "label": "SUV", "icon": "🚐"},
    {"id": "minivan", "label": "Minivan", "icon": "🚌"},
]


def _is_uploaded_file(value: Any) -> bool:
    return isinstance(value, (UploadFile, StarletteUploadFile))


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


def _pick_value(data: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    return None


def _normalize_features_input(raw_features: Any) -> List[str]:
    if raw_features is None:
        return []

    if isinstance(raw_features, list):
        return [str(item).strip() for item in raw_features if str(item).strip()]

    if isinstance(raw_features, str):
        return _parse_features(raw_features)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="features must be a list, JSON array string, or comma-separated string",
    )


async def _build_payload_from_request(request: Request) -> PostCreate:
    content_type = request.headers.get("content-type", "").lower()

    if "multipart/form-data" in content_type:
        form = await request.form()

        form_data: Dict[str, Any] = {}
        image_files: List[UploadFile] = []

        for key, value in form.multi_items():
            if _is_uploaded_file(value):
                if key in {"images", "files"}:
                    image_files.append(value)
                continue
            form_data[key] = value

        return PostCreate(
            post_title=str(_pick_value(form_data, "post_title", "postTitle") or ""),
            category=str(_pick_value(form_data, "category") or "sedan"),
            price_per_day=float(_pick_value(form_data, "price_per_day", "pricePerDay") or 0),
            location=str(_pick_value(form_data, "location") or ""),
            contact_number=str(_pick_value(form_data, "contact_number", "contactNumber") or ""),
            description=str(_pick_value(form_data, "description") or ""),
            features=_normalize_features_input(_pick_value(form_data, "features")),
            image_urls=await _save_images(image_files),
        )

    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request payload. Send JSON or multipart/form-data.",
        )

    if not isinstance(body, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request payload must be an object.",
        )

    return PostCreate(
        post_title=str(_pick_value(body, "post_title", "postTitle") or ""),
        category=str(_pick_value(body, "category") or "sedan"),
        price_per_day=float(_pick_value(body, "price_per_day", "pricePerDay") or 0),
        location=str(_pick_value(body, "location") or ""),
        contact_number=str(_pick_value(body, "contact_number", "contactNumber") or ""),
        description=str(_pick_value(body, "description") or ""),
        features=_normalize_features_input(_pick_value(body, "features")),
        image_urls=[
            str(url).strip()
            for url in (_pick_value(body, "image_urls", "imageUrls") or [])
            if str(url).strip()
        ],
    )


@router.post("", response_model=PostCreateResponse, status_code=status.HTTP_201_CREATED)
async def add_post(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        payload = await _build_payload_from_request(request)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="price_per_day must be a valid number",
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
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    safe_skip = max(skip, 0)
    safe_limit = min(max(limit, 1), 100)
    return get_posts(db, skip=safe_skip, limit=safe_limit, category=category)


@router.get("/categories", status_code=status.HTTP_200_OK)
def list_post_categories():
    return POST_CATEGORIES


@router.get("/me", response_model=List[PostOut], status_code=status.HTTP_200_OK)
def list_my_posts(
    skip: int = 0,
    limit: int = 20,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
):
    safe_skip = max(skip, 0)
    safe_limit = min(max(limit, 1), 100)

    # Backward compatibility for clients that call /posts/me before login.
    if current_user is None:
        return get_posts(db, skip=safe_skip, limit=safe_limit, category=category)

    return get_posts_by_owner(
        db,
        owner_id=current_user.id,
        skip=safe_skip,
        limit=safe_limit,
        category=category,
    )


@router.get("/{post_id}", response_model=PostOut, status_code=status.HTTP_200_OK)
def get_post(post_id: int, db: Session = Depends(get_db)):
    post = get_post_by_id(db, post_id=post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    return post


async def _build_update_payload_from_request(request: Request) -> tuple[PostCreate, list[str]]:
    """Returns (PostCreate, existing_image_urls_to_keep)."""
    content_type = request.headers.get("content-type", "").lower()

    if "multipart/form-data" in content_type:
        form = await request.form()

        form_data: Dict[str, Any] = {}
        image_files: List[UploadFile] = []

        for key, value in form.multi_items():
            if _is_uploaded_file(value):
                if key in {"images", "files"}:
                    image_files.append(value)
                continue
            form_data[key] = value

        raw_existing = _pick_value(form_data, "existing_image_urls", "existingImageUrls")
        existing_urls: List[str] = []
        if raw_existing:
            try:
                parsed = json.loads(raw_existing)
                if isinstance(parsed, list):
                    existing_urls = [str(u).strip() for u in parsed if str(u).strip()]
            except (json.JSONDecodeError, ValueError):
                pass

        new_image_urls = await _save_images(image_files)
        combined_image_urls = existing_urls + new_image_urls

        payload = PostCreate(
            post_title=str(_pick_value(form_data, "post_title", "postTitle") or ""),
            category=str(_pick_value(form_data, "category") or "sedan"),
            price_per_day=float(_pick_value(form_data, "price_per_day", "pricePerDay") or 0),
            location=str(_pick_value(form_data, "location") or ""),
            contact_number=str(_pick_value(form_data, "contact_number", "contactNumber") or ""),
            description=str(_pick_value(form_data, "description") or ""),
            features=_normalize_features_input(_pick_value(form_data, "features")),
            image_urls=combined_image_urls,
        )
        return payload, existing_urls

    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request payload. Send JSON or multipart/form-data.",
        )

    if not isinstance(body, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request payload must be an object.",
        )

    existing_urls = [
        str(u).strip()
        for u in (_pick_value(body, "existing_image_urls", "existingImageUrls") or [])
        if str(u).strip()
    ]
    new_image_urls_from_body = [
        str(url).strip()
        for url in (_pick_value(body, "image_urls", "imageUrls") or [])
        if str(url).strip()
    ]
    combined_image_urls = existing_urls + new_image_urls_from_body

    payload = PostCreate(
        post_title=str(_pick_value(body, "post_title", "postTitle") or ""),
        category=str(_pick_value(body, "category") or "sedan"),
        price_per_day=float(_pick_value(body, "price_per_day", "pricePerDay") or 0),
        location=str(_pick_value(body, "location") or ""),
        contact_number=str(_pick_value(body, "contact_number", "contactNumber") or ""),
        description=str(_pick_value(body, "description") or ""),
        features=_normalize_features_input(_pick_value(body, "features")),
        image_urls=combined_image_urls,
    )
    return payload, existing_urls


@router.put("/{post_id}", response_model=PostCreateResponse, status_code=status.HTTP_200_OK)
async def update_post_endpoint(
    post_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        payload, _ = await _build_update_payload_from_request(request)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="price_per_day must be a valid number",
        )

    post = update_post(
        db,
        post_id=post_id,
        owner_id=current_user.id,
        payload=payload,
        is_admin=(getattr(current_user, "role", None) == "admin"),
    )
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found or you do not have permission to edit it",
        )
    return {
        "message": "Post updated successfully.",
        "post": post,
    }


@router.delete("/{post_id}", status_code=status.HTTP_200_OK)
def delete_post_endpoint(
    post_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    success = delete_post(
        db,
        post_id=post_id,
        owner_id=current_user.id,
        is_admin=(getattr(current_user, "role", None) == "admin"),
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found or you do not have permission to delete it",
        )
    return {"message": "Post deleted successfully."}
