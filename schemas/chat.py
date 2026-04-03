from datetime import datetime
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
        return cleaned


class ChatMessageOut(BaseModel):
    id: int
    hire_request_id: int
    sender_id: int
    sender_name: Optional[str] = None
    sender_email: Optional[str] = None
    message: str
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }


class ActiveChatOut(BaseModel):
    hire_request_id: int
    hire_request_status: str
    requester_id: int
    requester_name: Optional[str] = None
    requester_email: Optional[str] = None
    owner_id: int
    owner_name: Optional[str] = None
    owner_email: Optional[str] = None
    vehicle_name: Optional[str] = None
    last_message: Optional[ChatMessageOut] = None
    updated_at: Optional[datetime] = None
