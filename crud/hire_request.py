from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from models.hire_request import HireRequest


def create_hire_request(
    db: Session,
    post_id: int,
    requester_id: int,
    owner_id: int,
    pickup_location: str,
    return_location: str,
    start_date,
    end_date,
    requested_price: Optional[float] = None,
    note: Optional[str] = None,
) -> HireRequest:
    hire_request = HireRequest(
        post_id=post_id,
        requester_id=requester_id,
        owner_id=owner_id,
        pickup_location=pickup_location,
        return_location=return_location,
        start_date=start_date,
        end_date=end_date,
        requested_price=requested_price,
        note=note,
        status="pending",
    )
    db.add(hire_request)
    db.commit()
    db.refresh(hire_request)
    return hire_request


def get_hire_request_by_id(db: Session, hire_request_id: int) -> Optional[HireRequest]:
    return db.query(HireRequest).filter(HireRequest.id == hire_request_id).first()


def get_hire_requests(db: Session, skip: int = 0, limit: int = 50) -> list[HireRequest]:
    return (
        db.query(HireRequest)
        .order_by(HireRequest.created_at.desc(), HireRequest.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_hire_requests_by_requester(db: Session, requester_id: int, skip: int = 0, limit: int = 50) -> list[HireRequest]:
    return (
        db.query(HireRequest)
        .filter(HireRequest.requester_id == requester_id)
        .order_by(HireRequest.created_at.desc(), HireRequest.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_hire_requests_by_owner(db: Session, owner_id: int, skip: int = 0, limit: int = 50) -> list[HireRequest]:
    return (
        db.query(HireRequest)
        .filter(HireRequest.owner_id == owner_id)
        .order_by(HireRequest.created_at.desc(), HireRequest.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_hire_request_status(
    db: Session,
    hire_request: HireRequest,
    status: str,
    admin_id: Optional[int] = None,
    rejection_reason: Optional[str] = None,
) -> HireRequest:
    hire_request.status = status
    hire_request.rejection_reason = rejection_reason if status == "rejected" else None
    hire_request.reviewed_by_admin_id = admin_id
    hire_request.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(hire_request)
    return hire_request
