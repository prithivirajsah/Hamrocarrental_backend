from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class ChatMessageCreate(BaseModel):
    message: str

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Message cannot be empty")
        if len(cleaned) > 2000:
            raise ValueError("Message must be 2000 characters or less")
        return cleaned


class ChatMessageOut(BaseModel):
    id: int
    hire_request_id: int
    hireRequestId: Optional[int] = None
    sender_id: int
    senderId: Optional[int] = None
    sender_name: Optional[str] = None
    senderName: Optional[str] = None
    sender_email: Optional[str] = None
    senderEmail: Optional[str] = None
    sender_role: Optional[str] = None
    senderRole: Optional[str] = None
    message: str
    created_at: datetime
    createdAt: Optional[datetime] = None

    model_config = {
        "from_attributes": True,
    }


class ActiveChatOut(BaseModel):
    id: int
    hire_request_id: int
    post_id: int
    status: str
    hire_request_status: str
    pickup_location: Optional[str] = None
    return_location: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    requested_price: Optional[float] = None
    note: Optional[str] = None
    requester_id: int
    requester_name: Optional[str] = None
    requester_email: Optional[str] = None
    owner_id: int
    owner_name: Optional[str] = None
    owner_email: Optional[str] = None
    vehicle_name: Optional[str] = None
    last_message: Optional[ChatMessageOut] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
