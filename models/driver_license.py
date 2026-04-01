# app/models/driver_license.py
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.sql import func
from database_connection import Base


class DriverLicense(Base):
    __tablename__ = "driver_licenses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    license_number = Column(String, nullable=False)
    license_image_url = Column(String, nullable=False)
    license_image_data = Column(LargeBinary, nullable=True)
    license_image_content_type = Column(String, nullable=True)
    license_image_filename = Column(String, nullable=True)
    license_expiry_date = Column(String, nullable=False)  # Format: YYYY-MM-DD
    verification_status = Column(
        Enum("pending", "verified", "rejected", name="license_verification_status"),
        nullable=False,
        default="pending",
        index=True
    )
    rejection_reason = Column(Text, nullable=True)  # Reason if rejected
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verified_by_admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
