from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ReviewCreate(BaseModel):
    post_id: int = Field(gt=0)
    rating: int = Field(ge=1, le=5)
    content: str

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Review content cannot be empty")
        return cleaned


class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    content: Optional[str] = None

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Review content cannot be empty")
        return cleaned


class ReviewLikeUpdate(BaseModel):
    delta: int = Field(default=1)

    @field_validator("delta")
    @classmethod
    def validate_delta(cls, value: int) -> int:
        if value not in (-1, 1):
            raise ValueError("delta must be either 1 or -1")
        return value


class ReviewOut(BaseModel):
    id: int
    post_id: int
    user_id: int
    rating: int
    content: str
    likes: int
    created_at: datetime
    updated_at: datetime
    user_name: Optional[str] = None
    role: str = "Customer"
    vehicle_name: Optional[str] = None

    model_config = {
        "from_attributes": True,
    }


class ReviewCreateResponse(BaseModel):
    message: str
    review: ReviewOut


class DriverReviewCreate(BaseModel):
    booking_id: int = Field(gt=0)
    rating: int = Field(ge=1, le=5)
    content: str

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Review content cannot be empty")
        return cleaned


class DriverReviewOut(BaseModel):
    id: int
    booking_id: Optional[int] = None
    post_id: Optional[int] = None
    driver_id: int
    reviewer_id: int
    rating: int
    content: str
    likes: int
    created_at: datetime
    updated_at: datetime
    reviewer_name: Optional[str] = None
    reviewer_email: Optional[str] = None
    driver_name: Optional[str] = None
    driver_email: Optional[str] = None
    vehicle_name: Optional[str] = None

    model_config = {
        "from_attributes": True,
    }


class DriverReviewCreateResponse(BaseModel):
    message: str
    review: DriverReviewOut


class DriverReviewSummaryOut(BaseModel):
    driver_id: int
    total_reviews: int
    average_rating: float


class ReviewReminderOut(BaseModel):
    booking_id: int
    post_id: int
    vehicle_name: Optional[str] = None
    owner_id: int
    start_date: date
    end_date: date
    completed_at: datetime
    message: str = "Your rental is completed. Please leave a review."

    model_config = {
        "from_attributes": True,
    }