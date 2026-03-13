# app/schemas.py
from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator, model_validator, validator

class UserRole(str, Enum):
    driver = "driver"
    user = "user"
    admin = "admin"

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole = UserRole.user

    @validator("full_name")
    def validate_full_name(cls, v):
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Full name must be at least 2 characters long")
        return v

class UserCreate(UserBase):
    password: str
    confirm_password: str

    # Password strength validator
    @field_validator("password")
    def password_strength(cls, v: str):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        if not any(c in "!@#$%^&*(),.?\":{}|<>" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v

    # New Pydantic v2 root validator
    @model_validator(mode="after")
    def check_passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self

class UserOut(UserBase):
    id: int
    phone: Optional[str] = None
    location: Optional[str] = None
    country: Optional[str] = None
    date_of_birth: Optional[date] = None
    is_active: bool
    created_at: datetime

    model_config = {
        "from_attributes": True
    }


class UserProfileUpdate(BaseModel):
    full_name: str
    phone: Optional[str] = None
    location: Optional[str] = None
    country: Optional[str] = None
    date_of_birth: Optional[date] = None

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("Full name must be at least 2 characters long")
        return cleaned

    @field_validator("phone", "location", "country")
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginResponse(Token):
    user: UserOut
    message: str


class GoogleAuthRequest(BaseModel):
    id_token: str
