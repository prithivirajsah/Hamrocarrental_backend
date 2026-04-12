from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from auth.jwt import get_current_user, is_admin_user
from crud.hire_request import (
    create_hire_request,
    get_hire_request_by_id,
    get_hire_requests,
    get_hire_requests_by_owner,
    get_hire_requests_by_requester,
    update_hire_request_status,
)
from crud.post import get_post_by_id
from crud.user import get_user_by_id
from database_connection import get_db
from schemas.hire_request import (
    HireRequestCreate,
    HireRequestCreateResponse,
    HireRequestOut,
    HireRequestStatusUpdate,
)
from utils.email_service import (
    send_hire_request_created_email,
    send_hire_request_status_updated_email,
)

router = APIRouter(prefix="/hire-requests", tags=["Hire Requests"])


def _require_owner_or_admin(hire_request, current_user) -> bool:
    if hire_request.owner_id == current_user.id:
        return True
    if is_admin_user(current_user):
        return True
    return False


def _to_hire_request_out(db: Session, hire_request) -> HireRequestOut:
    requester = get_user_by_id(db, hire_request.requester_id)
    owner = get_user_by_id(db, hire_request.owner_id)
    post = get_post_by_id(db, hire_request.post_id)

    return HireRequestOut(
        id=hire_request.id,
        post_id=hire_request.post_id,
        requester_id=hire_request.requester_id,
        owner_id=hire_request.owner_id,
        pickup_location=hire_request.pickup_location,
        return_location=hire_request.return_location,
        start_date=hire_request.start_date,
        end_date=hire_request.end_date,
        requested_price=hire_request.requested_price,
        note=hire_request.note,
        status=hire_request.status,
        rejection_reason=hire_request.rejection_reason,
        reviewed_at=hire_request.reviewed_at,
        created_at=hire_request.created_at,
        updated_at=hire_request.updated_at,
        requester_name=getattr(requester, "full_name", None),
        requester_email=getattr(requester, "email", None),
        owner_name=getattr(owner, "full_name", None),
        owner_email=getattr(owner, "email", None),
        vehicle_name=getattr(post, "post_title", None),
    )

@router.post("", response_model=HireRequestCreateResponse, status_code=status.HTTP_201_CREATED)
def add_hire_request(
    payload: HireRequestCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    post = get_post_by_id(db, payload.post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle post not found")

    if post.owner_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot request your own vehicle")

    if payload.start_date < date.today():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Start date cannot be in the past")

    hire_request = create_hire_request(
        db=db,
        post_id=post.id,
        requester_id=current_user.id,
        owner_id=post.owner_id,
        pickup_location=payload.pickup_location,
        return_location=payload.return_location,
        start_date=payload.start_date,
        end_date=payload.end_date,
        requested_price=payload.requested_price,
        note=payload.note,
    )

    requester = get_user_by_id(db, hire_request.requester_id)
    owner = get_user_by_id(db, hire_request.owner_id)
    background_tasks.add_task(send_hire_request_created_email, requester, owner, hire_request, post)

    return {
        "message": "Hire request created successfully.",
        "hire_request": _to_hire_request_out(db, hire_request),
    }


@router.get("", response_model=List[HireRequestOut], status_code=status.HTTP_200_OK)
def list_hire_requests(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    safe_skip = max(skip, 0)
    safe_limit = min(max(limit, 1), 100)

    if is_admin_user(current_user):
        records = get_hire_requests(db, skip=safe_skip, limit=safe_limit)
    else:
        records = get_hire_requests_by_requester(db, requester_id=current_user.id, skip=safe_skip, limit=safe_limit)

    return [_to_hire_request_out(db, hire_request) for hire_request in records]


@router.get("/me", response_model=List[HireRequestOut], status_code=status.HTTP_200_OK)
def list_my_hire_requests(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    safe_skip = max(skip, 0)
    safe_limit = min(max(limit, 1), 100)
    records = get_hire_requests_by_requester(db, requester_id=current_user.id, skip=safe_skip, limit=safe_limit)
    return [_to_hire_request_out(db, hire_request) for hire_request in records]


@router.get("/owner/me", response_model=List[HireRequestOut], status_code=status.HTTP_200_OK)
def list_owner_hire_requests(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    safe_skip = max(skip, 0)
    safe_limit = min(max(limit, 1), 100)
    records = get_hire_requests_by_owner(db, owner_id=current_user.id, skip=safe_skip, limit=safe_limit)
    return [_to_hire_request_out(db, hire_request) for hire_request in records]


@router.get("/{hire_request_id}", response_model=HireRequestOut, status_code=status.HTTP_200_OK)
def get_hire_request_details(
    hire_request_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    hire_request = get_hire_request_by_id(db, hire_request_id)
    if not hire_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hire request not found")

    is_requester = hire_request.requester_id == current_user.id
    is_owner = hire_request.owner_id == current_user.id
    is_admin = is_admin_user(current_user)
    if not (is_requester or is_owner or is_admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to access this request")

    return _to_hire_request_out(db, hire_request)


@router.patch("/{hire_request_id}/status", response_model=HireRequestOut, status_code=status.HTTP_200_OK)
def change_hire_request_status(
    hire_request_id: int,
    payload: HireRequestStatusUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    hire_request = get_hire_request_by_id(db, hire_request_id)
    if not hire_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hire request not found")

    normalized = payload.status.value
    if normalized == "rejected" and not (payload.rejection_reason or "").strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rejection_reason is required when rejecting")

    is_admin = is_admin_user(current_user)
    is_owner = hire_request.owner_id == current_user.id
    is_requester = hire_request.requester_id == current_user.id

    if not (is_admin or is_owner or is_requester):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to update this request")

    if is_owner and normalized not in {"approved", "rejected", "cancelled"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owners can only approve, reject, or cancel requests")

    if is_requester and normalized != "cancelled":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requesters can only cancel their own requests")

    updated = update_hire_request_status(
        db,
        hire_request=hire_request,
        status=normalized,
        admin_id=current_user.id if is_admin else None,
        rejection_reason=payload.rejection_reason,
    )
    requester = get_user_by_id(db, updated.requester_id)
    owner = get_user_by_id(db, updated.owner_id)
    background_tasks.add_task(send_hire_request_status_updated_email, requester, owner, updated, normalized, payload.rejection_reason)
    return _to_hire_request_out(db, updated)


@router.patch("/{hire_request_id}/accept", response_model=HireRequestOut, status_code=status.HTTP_200_OK)
def accept_hire_request(
    hire_request_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    hire_request = get_hire_request_by_id(db, hire_request_id)
    if not hire_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hire request not found")

    if not _require_owner_or_admin(hire_request, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the assigned driver/owner can accept this request")

    if hire_request.status == "approved":
        return _to_hire_request_out(db, hire_request)

    if hire_request.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only pending requests can be accepted")

    updated = update_hire_request_status(
        db,
        hire_request=hire_request,
        status="approved",
        admin_id=current_user.id if is_admin_user(current_user) else None,
        rejection_reason=None,
    )

    requester = get_user_by_id(db, updated.requester_id)
    owner = get_user_by_id(db, updated.owner_id)
    background_tasks.add_task(send_hire_request_status_updated_email, requester, owner, updated, "approved", None)
    return _to_hire_request_out(db, updated)


@router.get("/chats/me", response_model=List[HireRequestOut], status_code=status.HTTP_200_OK)
def list_my_chat_ready_hire_requests(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    records = get_hire_requests_by_requester(db, requester_id=current_user.id, skip=0, limit=200)
    records = [hire_request for hire_request in records if hire_request.status == "approved"]
    owner_records = get_hire_requests_by_owner(db, owner_id=current_user.id, skip=0, limit=200)
    owner_records = [hire_request for hire_request in owner_records if hire_request.status == "approved"]

    merged = {hire_request.id: hire_request for hire_request in records + owner_records}
    ordered = sorted(
        merged.values(),
        key=lambda hire_request: (hire_request.updated_at, hire_request.created_at, hire_request.id),
        reverse=True,
    )
    return [_to_hire_request_out(db, hire_request) for hire_request in ordered]
