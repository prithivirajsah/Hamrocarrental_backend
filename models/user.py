# app/models.py
from sqlalchemy import Boolean, Column, Date, DateTime, Enum, Integer, String
from sqlalchemy.sql import func
from database_connection import Base

# using string-backed enum to keep DB simple
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    role = Column(Enum("driver", "user", "admin", name="user_roles"), nullable=False, default="user")
    hashed_password = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    profile_image_url = Column(String, nullable=True)
    location = Column(String, nullable=True)
    country = Column(String, nullable=True)
    date_of_birth = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
