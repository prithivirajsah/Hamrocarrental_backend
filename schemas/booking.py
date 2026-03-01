from datetime import date, datetime
from enum import Enum
from pydantic import BaseModel, field_validator, model_validator


class BookingStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"


class BookingCreate(BaseModel):
    vehicle_type: str
    pickup_location: str
    dropoff_location: str
    pickup_date: date
    return_date: date

    @field_validator("vehicle_type", "pickup_location", "dropoff_location")
    def strip_and_validate_non_empty(cls, value: str):
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("This field cannot be empty")
        return cleaned

    @model_validator(mode="after")
    def validate_dates(self):
        if self.return_date < self.pickup_date:
            raise ValueError("Return date cannot be earlier than pickup date")
        return self


class BookingStatusUpdate(BaseModel):
    status: BookingStatus


class BookingOut(BaseModel):
    id: int
    user_id: int
    vehicle_type: str
    pickup_location: str
    dropoff_location: str
    pickup_date: date
    return_date: date
    status: BookingStatus
    created_at: datetime

    model_config = {"from_attributes": True}
