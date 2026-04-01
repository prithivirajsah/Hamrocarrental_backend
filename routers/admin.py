from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
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
