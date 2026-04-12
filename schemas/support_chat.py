from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class SupportMessageCreate(BaseModel):
    message: str

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("Message cannot be empty")
        if len(cleaned) > 2000:
            raise ValueError("Message must be 2000 characters or less")
        return cleaned


class SupportConversationCreate(BaseModel):
    create_new: bool = False


class SupportMessageOut(BaseModel):
    id: int
    conversation_id: int
    sender_id: int
    sender_name: Optional[str] = None
    sender_email: Optional[str] = None
    sender_role: Optional[str] = None
    message: str
    is_read: bool
    created_at: datetime


class SupportConversationSummaryOut(BaseModel):
    id: int
    user_id: int
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    is_open: bool
    unread_count_for_admin: int
    unread_count_for_user: int
    last_message: Optional[SupportMessageOut] = None
    created_at: datetime
    updated_at: datetime


class SupportConversationDetailOut(BaseModel):
    conversation: SupportConversationSummaryOut
    messages: list[SupportMessageOut]


class SupportReadReceiptOut(BaseModel):
    conversation_id: int
    marked_count: int
