from datetime import datetime
from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from models.hire_request import HireRequest
from models.post import Post


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


def get_hire_requests_for_owner_identity(db: Session, owner_id: int, skip: int = 0, limit: int = 50) -> list[HireRequest]:
    """Return requests owned by user, including legacy rows with stale owner_id.

    Some legacy records can have owner_id out of sync with posts.owner_id.
    We treat post ownership as a secondary source of truth.
    """
    return (
        db.query(HireRequest)
        .join(Post, Post.id == HireRequest.post_id)
        .filter(
            or_(
                HireRequest.owner_id == owner_id,
                Post.owner_id == owner_id,
            )
        )
        .order_by(HireRequest.created_at.desc(), HireRequest.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_hire_requests_for_driver_queue(db: Session, driver_id: int, skip: int = 0, limit: int = 50) -> list[HireRequest]:
    """Return requests visible to a driver.

    Drivers should always see:
    - their own requests (all statuses)
    - globally pending requests so they can accept and take ownership
    """
    return (
        db.query(HireRequest)
        .join(Post, Post.id == HireRequest.post_id)
        .filter(
            or_(
                HireRequest.owner_id == driver_id,
                Post.owner_id == driver_id,
                HireRequest.status == "pending",
            )
        )
        .order_by(HireRequest.created_at.desc(), HireRequest.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_hire_request_dashboard_stats_for_owner(db: Session, owner_id: int) -> dict:
    """Return hire-request stats for owner dashboard cards.

    The stats include requests where ownership is identified either directly from
    ``hire_requests.owner_id`` or indirectly via ``posts.owner_id`` for legacy rows.
    """
    base_query = (
        db.query(HireRequest)
        .join(Post, Post.id == HireRequest.post_id)
        .filter(
            or_(
                HireRequest.owner_id == owner_id,
                Post.owner_id == owner_id,
            )
        )
    )

    total_requests = base_query.with_entities(func.count(func.distinct(HireRequest.id))).scalar() or 0
    pending_requests = (
        base_query
        .filter(HireRequest.status == "pending")
        .with_entities(func.count(func.distinct(HireRequest.id)))
        .scalar()
        or 0
    )

    return {
        "hire_requests": int(total_requests),
        "pending_requests": int(pending_requests),
    }


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
