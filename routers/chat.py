from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth.jwt import get_current_user, is_admin_user
from crud.chat import (
    create_chat_message,
    get_active_hire_requests_for_user,
    get_chat_messages_for_hire_request,
    get_latest_chat_message,
)
from crud.hire_request import get_hire_request_by_id
from crud.post import get_post_by_id
from crud.user import get_user_by_id
from database_connection import get_db
from schemas.chat import ActiveChatOut, ChatMessageCreate, ChatMessageOut

router = APIRouter(prefix="/chats", tags=["Chats"])


def _to_chat_message_out(db: Session, chat_message) -> ChatMessageOut:
    sender = get_user_by_id(db, chat_message.sender_id)
    return ChatMessageOut(
        id=chat_message.id,
        hire_request_id=chat_message.hire_request_id,
        hireRequestId=chat_message.hire_request_id,
        sender_id=chat_message.sender_id,
        senderId=chat_message.sender_id,
        sender_name=getattr(sender, "full_name", None),
        senderName=getattr(sender, "full_name", None),
        sender_email=getattr(sender, "email", None),
        senderEmail=getattr(sender, "email", None),
        sender_role=getattr(sender, "role", None),
        senderRole=getattr(sender, "role", None),
        message=chat_message.message,
        created_at=chat_message.created_at,
        createdAt=chat_message.created_at,
    )


def _to_active_chat_out(db: Session, hire_request) -> ActiveChatOut:
    requester = get_user_by_id(db, hire_request.requester_id)
    owner = get_user_by_id(db, hire_request.owner_id)
    post = get_post_by_id(db, hire_request.post_id)
    latest_message = get_latest_chat_message(db, hire_request.id)

    return ActiveChatOut(
        id=hire_request.id,
        hire_request_id=hire_request.id,
        post_id=hire_request.post_id,
        status=hire_request.status,
        hire_request_status=hire_request.status,
        pickup_location=hire_request.pickup_location,
        return_location=hire_request.return_location,
        start_date=hire_request.start_date,
        end_date=hire_request.end_date,
        requested_price=hire_request.requested_price,
        note=hire_request.note,
        requester_id=hire_request.requester_id,
        requester_name=getattr(requester, "full_name", None),
        requester_email=getattr(requester, "email", None),
        owner_id=hire_request.owner_id,
        owner_name=getattr(owner, "full_name", None),
        owner_email=getattr(owner, "email", None),
        vehicle_name=getattr(post, "post_title", None),
        last_message=_to_chat_message_out(db, latest_message) if latest_message else None,
        created_at=hire_request.created_at,
        updated_at=hire_request.updated_at,
    )


@router.get("/me", response_model=List[ActiveChatOut], status_code=status.HTTP_200_OK)
def list_my_chats(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    hire_requests = get_active_hire_requests_for_user(db, current_user.id)
    return [_to_active_chat_out(db, hire_request) for hire_request in hire_requests]


@router.get("/{hire_request_id}/messages", response_model=List[ChatMessageOut], status_code=status.HTTP_200_OK)
def list_chat_messages(
    hire_request_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    hire_request = get_hire_request_by_id(db, hire_request_id)
    if not hire_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hire request not found")

    if current_user.id not in {hire_request.requester_id, hire_request.owner_id} and not is_admin_user(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this chat")

    if hire_request.status != "approved" and not is_admin_user(current_user):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chat is available after the hire request is approved")

    messages = get_chat_messages_for_hire_request(db, hire_request_id)
    return [_to_chat_message_out(db, message) for message in messages]


@router.post("/{hire_request_id}/messages", response_model=ChatMessageOut, status_code=status.HTTP_201_CREATED)
def send_chat_message(
    hire_request_id: int,
    payload: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    hire_request = get_hire_request_by_id(db, hire_request_id)
    if not hire_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hire request not found")

    if current_user.id not in {hire_request.requester_id, hire_request.owner_id}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this chat")

    if hire_request.status != "approved":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chat is available after the hire request is approved")

    chat_message = create_chat_message(
        db,
        hire_request_id=hire_request.id,
        sender_id=current_user.id,
        message=payload.message,
    )
    return _to_chat_message_out(db, chat_message)
