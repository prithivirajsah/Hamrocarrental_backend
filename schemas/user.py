# app/schemas.py
from pydantic import BaseModel, EmailStr, validator, field_validator, model_validator
from typing import Optional
from datetime import datetime
from enum import Enum

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
    is_active: bool
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginResponse(Token):
    user: UserOut
    message: str


class GoogleAuthRequest(BaseModel):
    id_token: str
