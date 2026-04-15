# app/routers/user_router.py

import os
import uuid
from io import BytesIO
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from PIL import Image
from pillow_heif import register_heif_opener
from sqlalchemy.orm import Session

from database_connection import get_db
from schemas.user import UserOut, UserProfileUpdate, UserRole
from crud.user import (
    get_all_drivers,
    get_user_by_id,
    get_users_by_role,
    get_all_drivers,
    count_users_by_role,
    update_user_profile,
    update_user_role,
    update_user_profile_image,
)
from auth.jwt import get_current_user, is_admin_user
from crud.driver_license import create_driver_license, get_driver_license_by_user_id
from crud.kyc import create_kyc_document, get_latest_user_kyc_document, get_user_approved_kyc_document
from pydantic import BaseModel


# Schema for driver license upload
class DriverLicenseUpload(BaseModel):
    license_number: str
    license_image_url: str
    license_expiry_date: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "license_number": "ABC123456",
                "license_image_url": "https://storage.example.com/license.jpg",
                "license_expiry_date": "2025-12-31"
            }
        }

router = APIRouter(prefix="/users", tags=["Users"])

KYC_UPLOAD_DIR = "static/uploads/kyc"
PROFILE_UPLOAD_DIR = "static/uploads/profiles"
os.makedirs(KYC_UPLOAD_DIR, exist_ok=True)
os.makedirs(PROFILE_UPLOAD_DIR, exist_ok=True)
ALLOWED_KYC_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}

ALLOWED_PROFILE_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}

HEIF_CONTENT_TYPES = {"image/heic", "image/heif"}

register_heif_opener()


def _driver_license_public_url() -> str:
    # Keep a stable URL so clients do not depend on storage filenames.
    return "/users/driver/license/image"


def _to_public_upload_path(url_value: Optional[str]) -> Optional[str]:
    if not url_value:
        return None

    normalized = url_value.strip().replace("\\", "/")
    marker = "static/uploads/"
    index = normalized.lower().find(marker)
    if index == -1:
        return None

    return normalized[index:]


def _normalize_upload_image(file: UploadFile, data: bytes) -> Dict[str, Any]:
    original_name = file.filename or "document"
    extension = os.path.splitext(original_name)[1].lower()
    is_heif_upload = file.content_type in HEIF_CONTENT_TYPES or extension in {".heic", ".heif"}

    if not is_heif_upload:
        return {
            "data": data,
            "extension": extension or ".jpg",
            "content_type": file.content_type or "application/octet-stream",
            "filename": original_name,
        }

    try:
        image = Image.open(BytesIO(data))
        converted = image.convert("RGB")
        buffer = BytesIO()
        converted.save(buffer, format="JPEG", quality=92)
        converted_data = buffer.getvalue()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to process HEIC/HEIF image. Please upload JPEG, PNG, or WEBP.",
        )

    stem = os.path.splitext(original_name)[0] or "document"
    return {
        "data": converted_data,
        "extension": ".jpg",
        "content_type": "image/jpeg",
        "filename": f"{stem}.jpg",
    }


async def _save_kyc_file(file: UploadFile) -> Dict[str, Any]:
    if file.content_type not in ALLOWED_KYC_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported document type: {file.content_type}",
        )

    raw_data = await file.read()
    normalized = _normalize_upload_image(file, raw_data)

    extension = normalized["extension"]
    file_name = f"{uuid.uuid4().hex}{extension}"
    file_path = os.path.join(KYC_UPLOAD_DIR, file_name)

    data = normalized["data"]
    with open(file_path, "wb") as output:
        output.write(data)

    return {
        "url": f"/static/uploads/kyc/{file_name}",
        "data": data,
        "content_type": normalized["content_type"],
        "filename": normalized["filename"],
    }


async def _save_profile_photo_file(file: UploadFile) -> Dict[str, Any]:
    if file.content_type not in ALLOWED_PROFILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported profile photo type: {file.content_type}",
        )

    raw_data = await file.read()
    normalized = _normalize_upload_image(file, raw_data)

    extension = normalized["extension"]
    file_name = f"{uuid.uuid4().hex}{extension}"
    file_path = os.path.join(PROFILE_UPLOAD_DIR, file_name)

    data = normalized["data"]
    with open(file_path, "wb") as output:
        output.write(data)

    return {
        "url": f"/static/uploads/profiles/{file_name}",
        "path": file_path,
    }


# Role-based feature lists
def get_role_features(role: str):
    features = {
        "admin": {
            "user_management": "Manage users and roles",
            "system_statistics": "View system analytics",
            "content_moderation": "Moderate listings and reviews",
        },
        "driver": {
            "my_vehicles": "Manage your vehicle listings",
            "earnings": "Track your earnings",
            "availability": "Update your availability status",
            "rental_requests": "View rental requests",
        },
        "user": {
            "favorites": "Your favorite vehicles",
            "reviews": "Rate and review your rentals",
            "notifications": "View notifications",
        },
    }
    return features.get(role, features["user"])

# Get current logged-in user
@router.get("/me", response_model=UserOut)
def read_current_user(current_user=Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserOut)
def update_current_user(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return update_user_profile(db, current_user, payload)


@router.post("/me/profile-photo", response_model=UserOut, status_code=status.HTTP_200_OK)
async def upload_profile_photo(
    profile_photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not profile_photo:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="profile_photo is required",
        )

    saved_photo = await _save_profile_photo_file(profile_photo)
    previous_image_url = current_user.profile_image_url

    try:
        updated_user = update_user_profile_image(db, current_user, saved_photo["url"])
    except Exception:
        try:
            os.remove(saved_photo["path"])
        except OSError:
            pass
        raise

    if previous_image_url and previous_image_url.startswith("/static/uploads/profiles/"):
        previous_path = previous_image_url.lstrip("/")
        if previous_path != saved_photo["path"] and os.path.exists(previous_path):
            try:
                os.remove(previous_path)
            except OSError:
                pass

    return updated_user

# Home Page for logged-in users
@router.get("/home")
def home_page(current_user=Depends(get_current_user)):
    return {
        "message": f"Welcome to Hamro Car Rental, {current_user.full_name}!",
        "user_role": current_user.role,
        "user_id": current_user.id,
        "features": {
            "browse_vehicles": "Browse available vehicles",
            "my_bookings": "View your booking history",
            "profile": "Edit profile",
            "support": "Get customer support",
        },
        "role_specific_features": get_role_features(current_user.role),
    }

# Admin: Get users by role
@router.get("/by-role/{role}", response_model=List[UserOut])
def get_users_by_role_endpoint(
    role: UserRole,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view users by role",
        )

    return get_users_by_role(db, role.value, skip, limit)

# Get all drivers (drivers only)
@router.get("/drivers", response_model=List[UserOut])
def get_drivers(
    skip: int = Query(0),
    limit: int = Query(100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return get_all_drivers(db, skip, limit)


# -------------------------------------------------
# Admin: Count users by role
# -------------------------------------------------
@router.get("/stats/roles")
def get_role_statistics(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view statistics",
        )

    return count_users_by_role(db)


# -------------------------------------------------
# Admin: Update a user's role
# -------------------------------------------------
@router.put("/{user_id}/role", response_model=UserOut)
def update_user_role_endpoint(
    user_id: int,
    new_role: UserRole,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update roles",
        )

    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role",
        )

    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    updated_user = update_user_role(db, user_id, new_role.value)
    return updated_user

# Driver: Upload License for verification
@router.post("/driver/license", status_code=status.HTTP_201_CREATED)
def upload_driver_license(
    license_data: DriverLicenseUpload,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Upload driver license for verification (driver role only)"""
    if current_user.role != "driver":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can upload license",
        )
    
    license = create_driver_license(
        db,
        user_id=current_user.id,
        license_number=license_data.license_number,
        license_image_url=license_data.license_image_url,
        license_expiry_date=license_data.license_expiry_date,
    )
    
    return {
        "id": license.id,
        "user_id": license.user_id,
        "license_number": license.license_number,
        "license_image_url": _driver_license_public_url(),
        "license_expiry_date": license.license_expiry_date,
        "verification_status": license.verification_status,
        "created_at": license.created_at,
    }


@router.get("/driver/license")
def get_my_driver_license(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get current driver's license verification status"""
    if current_user.role != "driver":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can view their license",
        )
    
    license = get_driver_license_by_user_id(db, current_user.id)
    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No license found. Please upload your license for verification.",
        )
    
    return {
        "id": license.id,
        "user_id": license.user_id,
        "license_number": license.license_number,
        "license_image_url": _driver_license_public_url(),
        "license_expiry_date": license.license_expiry_date,
        "verification_status": license.verification_status,
        "rejection_reason": license.rejection_reason,
        "verified_at": license.verified_at,
        "created_at": license.created_at,
    }


@router.get("/driver/license/image", include_in_schema=False)
def get_my_driver_license_image(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Serve the current driver's uploaded license image/document."""
    if current_user.role != "driver":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can view their license",
        )

    license_row = get_driver_license_by_user_id(db, current_user.id)
    if not license_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No license found. Please upload your license for verification.",
        )

    if license_row.license_image_data:
        return Response(
            content=license_row.license_image_data,
            media_type=license_row.license_image_content_type or "application/octet-stream",
        )

    path_from_url = _to_public_upload_path(license_row.license_image_url)
    if path_from_url and os.path.isfile(path_from_url):
        with open(path_from_url, "rb") as input_file:
            raw_data = input_file.read()

        guessed_type = license_row.license_image_content_type
        if not guessed_type:
            ext = os.path.splitext(path_from_url)[1].lower()
            if ext == ".pdf":
                guessed_type = "application/pdf"
            elif ext in {".jpg", ".jpeg"}:
                guessed_type = "image/jpeg"
            elif ext == ".png":
                guessed_type = "image/png"
            elif ext == ".webp":
                guessed_type = "image/webp"

        return Response(content=raw_data, media_type=guessed_type or "application/octet-stream")

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="License image not found")


@router.post("/kyc-documents", status_code=status.HTTP_201_CREATED)
async def upload_kyc_documents(
    document_type: str = Form(...),
    document_number: str = Form(...),
    front_file: UploadFile = File(...),
    back_file: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    front_saved = await _save_kyc_file(front_file)
    back_saved = await _save_kyc_file(back_file) if back_file else None

    document = create_kyc_document(
        db,
        user_id=current_user.id,
        document_type=document_type,
        document_number=document_number,
        front_image_url=front_saved["url"],
        back_image_url=back_saved["url"] if back_saved else None,
        front_image_data=front_saved["data"],
        front_image_content_type=front_saved["content_type"],
        front_image_filename=front_saved["filename"],
        back_image_data=back_saved["data"] if back_saved else None,
        back_image_content_type=back_saved["content_type"] if back_saved else None,
        back_image_filename=back_saved["filename"] if back_saved else None,
    )

    return {
        "id": document.id,
        "user_id": document.user_id,
        "document_type": document.document_type,
        "document_number": document.document_number,
        "front_image_url": document.front_image_url,
        "back_image_url": document.back_image_url,
        "verification_status": document.verification_status,
        "created_at": document.created_at,
    }


@router.get("/kyc-documents/me")
def get_my_kyc_document(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    document = get_latest_user_kyc_document(db, current_user.id)
    if not document:
        return {
            "has_document": False,
            "document": None,
        }

    return {
        "has_document": True,
        "document": {
        "id": document.id,
        "user_id": document.user_id,
        "document_type": document.document_type,
        "document_number": document.document_number,
        "front_image_url": document.front_image_url,
        "back_image_url": document.back_image_url,
        "verification_status": document.verification_status,
        "rejection_reason": document.rejection_reason,
        "reviewed_at": document.reviewed_at,
        "created_at": document.created_at,
        },
    }


@router.get("/kyc-document/me")
def get_my_kyc_document_alias(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return get_my_kyc_document(db=db, current_user=current_user)


@router.get("/me/verification")
def get_my_verification_status(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Unified profile verification endpoint for frontend consumption."""
    approved_kyc = get_user_approved_kyc_document(db, current_user.id)
    latest_kyc = approved_kyc or get_latest_user_kyc_document(db, current_user.id)
    license_row = get_driver_license_by_user_id(db, current_user.id)

    kyc_status = latest_kyc.verification_status if latest_kyc else "not_submitted"
    kyc_can_upload = kyc_status != "approved"

    if license_row:
        license_status = license_row.verification_status
        license_document_url = _driver_license_public_url()
    else:
        license_status = "not_submitted"
        license_document_url = None

    return {
        "user": UserOut.model_validate(current_user),
        "kyc": {
            "status": kyc_status,
            "can_upload": kyc_can_upload,
            "is_verified": kyc_status == "approved",
            "document_id": latest_kyc.id if latest_kyc else None,
            "reviewed_at": latest_kyc.reviewed_at if latest_kyc else None,
            "rejection_reason": latest_kyc.rejection_reason if latest_kyc else None,
        },
        "driver_license": {
            "status": license_status,
            "is_verified": license_status == "verified",
            "document_url": license_document_url,
            "license_id": license_row.id if license_row else None,
            "verified_at": license_row.verified_at if license_row else None,
            "rejection_reason": license_row.rejection_reason if license_row else None,
        },
    }
