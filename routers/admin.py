import os
from io import BytesIO
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from PIL import Image
from pillow_heif import register_heif_opener
from sqlalchemy.orm import Session

from auth.jwt import get_current_admin
from crud.admin import (
    get_admin_dashboard_data,
    get_admin_users,
    get_admin_posts,
    get_admin_messages,
    get_pending_driver_licenses,
    get_all_driver_licenses,
    verify_driver_license,
    reject_driver_license,
)
from crud.kyc import get_admin_kyc_documents, update_kyc_status
from database_connection import get_db
from models.driver_license import DriverLicense
from models.kyc_document import KycDocument
from schemas.admin import (
    AdminDashboardResponse,
    AdminPostListItem,
    DriverLicenseItem,
    DriverLicenseVerifyRequest,
    DriverLicenseVerifyResponse,
)
from schemas.user import UserOut
from schemas.kyc import KycDocumentOut, KycStatusUpdateRequest, KycStatusUpdateResponse
from schemas.contact import ContactMessageOut


router = APIRouter(prefix="/admin", tags=["Admin"])
register_heif_opener()


def _to_public_upload_path(url_value: Optional[str]) -> Optional[str]:
    if not url_value:
        return None

    normalized = url_value.strip().replace("\\", "/")
    marker = "static/uploads/"
    index = normalized.lower().find(marker)
    if index == -1:
        return None

    return normalized[index:]


def _coerce_image_for_preview(image_bytes: bytes, content_type: Optional[str]) -> tuple[bytes, str]:
    normalized_type = (content_type or "").lower()
    if normalized_type in {"image/heic", "image/heif"}:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=92)
        return buffer.getvalue(), "image/jpeg"
    return image_bytes, content_type or "application/octet-stream"


def _preview_response_from_document(document: KycDocument, side: str) -> Response:
    if side == "front":
        binary = document.front_image_data
        content_type = document.front_image_content_type
        url = document.front_image_url
    else:
        binary = document.back_image_data
        content_type = document.back_image_content_type
        url = document.back_image_url

    if binary:
        data, media_type = _coerce_image_for_preview(binary, content_type)
        return Response(content=data, media_type=media_type)

    path_from_url = _to_public_upload_path(url)
    if path_from_url and os.path.isfile(path_from_url):
        with open(path_from_url, "rb") as input_file:
            raw_data = input_file.read()
        guessed_type = content_type
        if not guessed_type:
            ext = os.path.splitext(path_from_url)[1].lower()
            if ext in {".heic", ".heif"}:
                guessed_type = "image/heic"
        data, media_type = _coerce_image_for_preview(raw_data, guessed_type)
        return Response(content=data, media_type=media_type)

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KYC image not found")


@router.get("/dashboard", response_model=AdminDashboardResponse, status_code=status.HTTP_200_OK)
def admin_dashboard(
    recent_limit: int = Query(8, ge=1, le=50),
    db: Session = Depends(get_db),
    _current_admin=Depends(get_current_admin),
):
    # Access is enforced via get_current_admin, which validates JWT and role.
    return get_admin_dashboard_data(db, recent_limit=recent_limit)


@router.get("/posts", response_model=List[AdminPostListItem], status_code=status.HTTP_200_OK)
def admin_posts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=300),
    search: Optional[str] = Query(None),
    owner_role: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _current_admin=Depends(get_current_admin),
):
    return get_admin_posts(
        db,
        skip=skip,
        limit=limit,
        search=search,
        owner_role=owner_role,
    )


@router.get("/users", response_model=List[UserOut], status_code=status.HTTP_200_OK)
def admin_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _current_admin=Depends(get_current_admin),
):
    return get_admin_users(
        db,
        skip=skip,
        limit=limit,
        search=search,
    )


@router.get("/messages", response_model=List[ContactMessageOut], status_code=status.HTTP_200_OK)
def admin_messages(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _current_admin=Depends(get_current_admin),
):
    """Get all contact messages with optional search"""
    return get_admin_messages(
        db,
        skip=skip,
        limit=limit,
        search=search,
    )


@router.get("/driver-licenses/pending", response_model=List[DriverLicenseItem], status_code=status.HTTP_200_OK)
def get_pending_licenses(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=300),
    db: Session = Depends(get_db),
    _current_admin=Depends(get_current_admin),
):
    """Get all pending driver license verifications"""
    return get_pending_driver_licenses(db, skip=skip, limit=limit)


@router.get("/driver-licenses", response_model=List[DriverLicenseItem], status_code=status.HTTP_200_OK)
def get_all_licenses(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=300),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _current_admin=Depends(get_current_admin),
):
    """Get all driver licenses with optional status filter"""
    return get_all_driver_licenses(db, skip=skip, limit=limit, status=status)


@router.get("/driver-licenses/{license_id}/image", include_in_schema=False)
def get_driver_license_image(
    license_id: int,
    db: Session = Depends(get_db),
    _current_admin=Depends(get_current_admin),
):
    license_row = db.query(DriverLicense).filter(DriverLicense.id == license_id).first()
    if not license_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="License not found")

    if license_row.license_image_data:
        data, media_type = _coerce_image_for_preview(
            license_row.license_image_data,
            license_row.license_image_content_type,
        )
        return Response(
            content=data,
            media_type=media_type,
        )

    path_from_url = _to_public_upload_path(license_row.license_image_url)
    if path_from_url and os.path.isfile(path_from_url):
        with open(path_from_url, "rb") as input_file:
            raw_data = input_file.read()
        guessed_type = license_row.license_image_content_type
        if not guessed_type:
            ext = os.path.splitext(path_from_url)[1].lower()
            if ext in {".heic", ".heif"}:
                guessed_type = "image/heic"
            elif ext in {".jpg", ".jpeg"}:
                guessed_type = "image/jpeg"
            elif ext == ".png":
                guessed_type = "image/png"
            elif ext == ".webp":
                guessed_type = "image/webp"
            elif ext == ".pdf":
                guessed_type = "application/pdf"
        data, media_type = _coerce_image_for_preview(raw_data, guessed_type)
        return Response(content=data, media_type=media_type)

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="License image not found")


@router.post("/driver-license/verify", response_model=DriverLicenseVerifyResponse, status_code=status.HTTP_200_OK)
def verify_license(
    request: DriverLicenseVerifyRequest,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """Verify or reject a driver license"""
    if request.action == "verify":
        result = verify_driver_license(db, request.license_id, current_admin.id)
    elif request.action == "reject":
        if not request.rejection_reason:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="rejection_reason is required for rejections",
            )
        result = reject_driver_license(db, request.license_id, current_admin.id, request.rejection_reason)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="action must be 'verify' or 'reject'",
        )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="License not found",
        )
    
    return result


@router.get("/kyc-documents", response_model=List[KycDocumentOut], status_code=status.HTTP_200_OK)
def list_kyc_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=300),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _current_admin=Depends(get_current_admin),
):
    return get_admin_kyc_documents(
        db,
        skip=skip,
        limit=limit,
        status=status,
        search=search,
    )


@router.get("/kyc-documents/{document_id}/front-image", include_in_schema=False)
def get_kyc_front_image(
    document_id: int,
    db: Session = Depends(get_db),
    _current_admin=Depends(get_current_admin),
):
    document = db.query(KycDocument).filter(KycDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KYC document not found")
    return _preview_response_from_document(document, side="front")


@router.get("/kyc-documents/{document_id}/back-image", include_in_schema=False)
def get_kyc_back_image(
    document_id: int,
    db: Session = Depends(get_db),
    _current_admin=Depends(get_current_admin),
):
    document = db.query(KycDocument).filter(KycDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KYC document not found")
    return _preview_response_from_document(document, side="back")


@router.patch("/kyc-documents/{document_id}/status", response_model=KycStatusUpdateResponse, status_code=status.HTTP_200_OK)
def change_kyc_status(
    document_id: int,
    payload: KycStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    normalized = (payload.status or "").strip().lower()
    if normalized not in {"pending", "approved", "rejected"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="status must be pending, approved, or rejected",
        )

    if normalized == "rejected" and not (payload.rejection_reason or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="rejection_reason is required when rejecting",
        )

    result = update_kyc_status(
        db,
        document_id=document_id,
        admin_id=current_admin.id,
        status=normalized,
        rejection_reason=payload.rejection_reason,
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KYC document not found")

    return result
