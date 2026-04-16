from datetime import datetime
from typing import List

from pydantic import BaseModel, field_validator


class PostCreate(BaseModel):
    post_title: str
    category: str = "sedan"
    price_per_day: float
    location: str
    contact_number: str
    description: str
    features: List[str] = []
    image_urls: List[str] = []

    @field_validator("post_title", "location", "contact_number", "description")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("This field cannot be empty")
        return cleaned

    @field_validator("price_per_day")
    @classmethod
    def validate_price(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("Price per day must be greater than 0")
        return value

    @field_validator("features")
    @classmethod
    def normalize_features(cls, value: List[str]) -> List[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        return cleaned

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str) -> str:
        cleaned = (value or "").strip().lower()
        if not cleaned:
            return "sedan"
        return cleaned


class PostOut(BaseModel):
    id: int
    owner_id: int
    post_title: str
    category: str
    price_per_day: float
    location: str
    contact_number: str
    description: str
    features: List[str]
    image_urls: List[str]
    status: str = "available"
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }


class PostStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        allowed = {"available", "booked", "maintenance"}
        cleaned = (value or "").strip().lower()
        if cleaned not in allowed:
            raise ValueError(f"Status must be one of: {', '.join(allowed)}")
        return cleaned


class PostCreateResponse(BaseModel):
    message: str
    post: PostOut
