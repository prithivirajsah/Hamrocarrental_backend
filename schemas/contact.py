from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional


class ContactMessageCreate(BaseModel):
    full_name: str
    email: EmailStr
    subject: str
    topic: str
    phone_number: Optional[str] = None
    message: str

    @field_validator("full_name", "subject", "topic", "message")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("This field cannot be empty")
        return cleaned

    @field_validator("phone_number")
    @classmethod
    def normalize_phone_number(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ContactMessageOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    subject: str
    topic: str
    phone_number: Optional[str]
    message: str
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }


class ContactSubmitResponse(BaseModel):
    message: str
    contact: ContactMessageOut
