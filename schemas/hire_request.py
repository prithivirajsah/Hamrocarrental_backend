from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, field_validator


class HireRequestStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"


class HireRequestCreate(BaseModel):
    post_id: int
    pickup_location: str
    return_location: str
    start_date: date
    end_date: date
    requested_price: Optional[float] = None
    note: Optional[str] = None

    @field_validator("pickup_location", "return_location")
    @classmethod
    def validate_locations(cls, value: str) -> str:
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


class HireRequestOut(BaseModel):
    id: int
    post_id: int
    requester_id: int
    owner_id: int
    pickup_location: str
    return_location: str
    start_date: date
    end_date: date
    requested_price: Optional[float] = None
    note: Optional[str] = None
    status: HireRequestStatus
    rejection_reason: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    requester_name: Optional[str] = None
    requester_email: Optional[str] = None
    owner_name: Optional[str] = None
    owner_email: Optional[str] = None
    vehicle_name: Optional[str] = None

    model_config = {
        "from_attributes": True,
    }


class HireRequestCreateResponse(BaseModel):
    message: str
    hire_request: HireRequestOut


class HireRequestStatusUpdate(BaseModel):
    status: HireRequestStatus
    rejection_reason: Optional[str] = None


class HireRequestOwnerDashboardStats(BaseModel):
    hire_requests: int
    pending_requests: int

