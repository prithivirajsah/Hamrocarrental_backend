from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from models.hire_request import HireRequest
from models.hire_request_message import HireRequestMessage
from models.user import User


def get_active_hire_requests_for_user(db: Session, user_id: int) -> List[HireRequest]:
    return (
        db.query(HireRequest)
        .filter(
            (HireRequest.requester_id == user_id)
            | (HireRequest.owner_id == user_id)
        )
        .filter(HireRequest.status == "approved")
        .order_by(HireRequest.updated_at.desc(), HireRequest.created_at.desc(), HireRequest.id.desc())
        .all()
    )


def get_chat_messages_for_hire_request(db: Session, hire_request_id: int) -> List[HireRequestMessage]:
    return (
        db.query(HireRequestMessage)
        .filter(HireRequestMessage.hire_request_id == hire_request_id)
        .order_by(HireRequestMessage.created_at.asc(), HireRequestMessage.id.asc())
        .all()
    )


def create_chat_message(
    db: Session,
    hire_request_id: int,
    sender_id: int,
    message: str,
) -> HireRequestMessage:
    chat_message = HireRequestMessage(
        hire_request_id=hire_request_id,
        sender_id=sender_id,
        message=message,
    )
    db.add(chat_message)

    hire_request = db.query(HireRequest).filter(HireRequest.id == hire_request_id).first()
    if hire_request:
        hire_request.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(chat_message)
    return chat_message


def get_latest_chat_message(db: Session, hire_request_id: int) -> Optional[HireRequestMessage]:
    return (
        db.query(HireRequestMessage)
        .filter(HireRequestMessage.hire_request_id == hire_request_id)
        .order_by(HireRequestMessage.created_at.desc(), HireRequestMessage.id.desc())
        .first()
    )
