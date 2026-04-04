from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, field_validator


class BookingStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


class BookingCreate(BaseModel):
    post_id: int
    pickup_location: str
    return_location: str
    start_date: date
    end_date: date
    note: Optional[str] = None

    @field_validator("pickup_location", "return_location")
    @classmethod
    def validate_non_empty_location(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Location cannot be empty")
        return cleaned

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("end_date")
    @classmethod
    def validate_dates(cls, end_date: date, info):
        start_date = info.data.get("start_date")
        if start_date and end_date < start_date:
            raise ValueError("End date must be greater than or equal to start date")
        return end_date


class BookingOut(BaseModel):
    id: int
    post_id: int
    user_id: int
    owner_id: int
    pickup_location: str
    return_location: str
    start_date: date
    end_date: date
    status: BookingStatus
    note: Optional[str]
    created_at: datetime

    user_name: Optional[str] = None
    user_email: Optional[str] = None
    vehicle_name: Optional[str] = None

    model_config = {
        "from_attributes": True,
    }


class BookingCreateResponse(BaseModel):
    message: str
    booking: BookingOut


class BookingStatusUpdate(BaseModel):
    status: BookingStatus


class BookingAvailabilityResponse(BaseModel):
    post_id: int
    start_date: date
    end_date: date
    available: bool
