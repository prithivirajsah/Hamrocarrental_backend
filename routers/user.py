# app/routers/user_router.py

import os
import uuid
from io import BytesIO
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
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
    update_user_role
)
from auth.jwt import get_current_user, is_admin_user
from crud.driver_license import create_driver_license, get_driver_license_by_user_id
from crud.kyc import create_kyc_document, get_latest_user_kyc_document
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
os.makedirs(KYC_UPLOAD_DIR, exist_ok=True)
ALLOWED_KYC_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}

HEIF_CONTENT_TYPES = {"image/heic", "image/heif"}

register_heif_opener()


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
        "license_image_url": license.license_image_url,
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
        "license_image_url": license.license_image_url,
        "license_expiry_date": license.license_expiry_date,
        "verification_status": license.verification_status,
        "rejection_reason": license.rejection_reason,
        "verified_at": license.verified_at,
        "created_at": license.created_at,
    }


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
