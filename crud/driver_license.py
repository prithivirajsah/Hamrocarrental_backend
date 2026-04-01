# app/crud/driver_license.py
from typing import Optional

from sqlalchemy.orm import Session
from models.driver_license import DriverLicense


def create_driver_license(
    db: Session,
    user_id: int,
    license_number: str,
    license_image_url: str,
    license_expiry_date: str,
    license_image_data: Optional[bytes] = None,
    license_image_content_type: Optional[str] = None,
    license_image_filename: Optional[str] = None,
):
    """Create a new driver license verification record"""
    # Check if user already has a license
    existing = db.query(DriverLicense).filter(DriverLicense.user_id == user_id).first()
    if existing:
        # Update the existing license
        existing.license_number = license_number
        existing.license_image_url = license_image_url
        existing.license_image_data = license_image_data
        existing.license_image_content_type = license_image_content_type
        existing.license_image_filename = license_image_filename
        existing.license_expiry_date = license_expiry_date
        existing.verification_status = "pending"  # Reset to pending if someone resubmits
        db.commit()
        db.refresh(existing)
        return existing
    
    license = DriverLicense(
        user_id=user_id,
        license_number=license_number,
        license_image_url=license_image_url,
        license_image_data=license_image_data,
        license_image_content_type=license_image_content_type,
        license_image_filename=license_image_filename,
        license_expiry_date=license_expiry_date,
        verification_status="pending",
    )
    db.add(license)
    db.commit()
    db.refresh(license)
    return license


def get_driver_license_by_user_id(db: Session, user_id: int):
    """Get driver license for a specific user"""
    return db.query(DriverLicense).filter(DriverLicense.user_id == user_id).first()
