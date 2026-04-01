from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from models.booking import Booking
from models.contact import ContactMessage
from models.post import Post
from models.user import User
from models.driver_license import DriverLicense


def get_admin_users(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
):
    query = db.query(User)

    normalized_search = (search or "").strip().lower()
    if normalized_search:
        like = f"%{normalized_search}%"
        query = query.filter(
            User.full_name.ilike(like)
            | User.email.ilike(like)
            | User.role.ilike(like)
        )

    return (
        query
        .order_by(User.created_at.desc(), User.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_admin_posts(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    owner_role: Optional[str] = None,
):
    query = (
        db.query(Post, User)
        .outerjoin(User, Post.owner_id == User.id)
    )

    normalized_role = (owner_role or "").strip().lower()
    if normalized_role in {"admin", "user", "driver"}:
        query = query.filter(User.role == normalized_role)

    normalized_search = (search or "").strip().lower()
    if normalized_search:
        like = f"%{normalized_search}%"
        query = query.filter(
            Post.post_title.ilike(like)
            | Post.category.ilike(like)
            | Post.location.ilike(like)
            | User.full_name.ilike(like)
            | User.email.ilike(like)
        )

    rows = (
        query
        .order_by(Post.created_at.desc(), Post.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        {
            "id": post.id,
            "owner_id": post.owner_id,
            "owner_name": getattr(owner, "full_name", None),
            "owner_email": getattr(owner, "email", None),
            "owner_role": getattr(owner, "role", None),
            "post_title": post.post_title,
            "category": post.category,
            "price_per_day": float(post.price_per_day),
            "location": post.location,
            "contact_number": post.contact_number,
            "description": post.description,
            "features": post.features or [],
            "image_urls": post.image_urls or [],
            "created_at": post.created_at,
        }
        for post, owner in rows
    ]


def get_admin_messages(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
):
    """Get all contact messages with optional search"""
    query = db.query(ContactMessage)

    normalized_search = (search or "").strip().lower()
    if normalized_search:
        like = f"%{normalized_search}%"
        query = query.filter(
            ContactMessage.full_name.ilike(like)
            | ContactMessage.email.ilike(like)
            | ContactMessage.subject.ilike(like)
            | ContactMessage.topic.ilike(like)
            | ContactMessage.message.ilike(like)
        )

    return (
        query
        .order_by(ContactMessage.created_at.desc(), ContactMessage.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_admin_dashboard_data(db: Session, recent_limit: int = 8):
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_admins = db.query(func.count(User.id)).filter(User.role == "admin").scalar() or 0
    total_drivers = db.query(func.count(User.id)).filter(User.role == "driver").scalar() or 0

    total_posts = db.query(func.count(Post.id)).scalar() or 0
    total_bookings = db.query(func.count(Booking.id)).scalar() or 0

    booking_counts_raw = (
        db.query(Booking.status, func.count(Booking.id))
        .group_by(Booking.status)
        .all()
    )
    booking_status_breakdown = {status: count for status, count in booking_counts_raw if status}

    pending_bookings = booking_status_breakdown.get("pending", 0)
    confirmed_bookings = booking_status_breakdown.get("confirmed", 0)
    completed_bookings = booking_status_breakdown.get("completed", 0)
    cancelled_bookings = booking_status_breakdown.get("cancelled", 0)

    total_revenue = (
        db.query(func.coalesce(func.sum(Booking.total_price), 0.0))
        .filter(Booking.status.in_(["confirmed", "completed"]))
        .scalar()
        or 0.0
    )

    recent_bookings_raw = (
        db.query(Booking, User, Post)
        .outerjoin(User, Booking.user_id == User.id)
        .outerjoin(Post, Booking.post_id == Post.id)
        .order_by(Booking.created_at.desc(), Booking.id.desc())
        .limit(recent_limit)
        .all()
    )

    recent_posts_raw = (
        db.query(Post, User)
        .outerjoin(User, Post.owner_id == User.id)
        .order_by(Post.created_at.desc(), Post.id.desc())
        .limit(recent_limit)
        .all()
    )

    recent_contacts = (
        db.query(ContactMessage)
        .order_by(ContactMessage.created_at.desc(), ContactMessage.id.desc())
        .limit(recent_limit)
        .all()
    )

    return {
        "stats": {
            "total_users": total_users,
            "total_admins": total_admins,
            "total_drivers": total_drivers,
            "total_posts": total_posts,
            "total_bookings": total_bookings,
            "pending_bookings": pending_bookings,
            "confirmed_bookings": confirmed_bookings,
            "completed_bookings": completed_bookings,
            "cancelled_bookings": cancelled_bookings,
            "total_revenue": float(total_revenue),
        },
        "booking_status_breakdown": booking_status_breakdown,
        "recent_bookings": [
            {
                "id": booking.id,
                "post_id": booking.post_id,
                "user_id": booking.user_id,
                "owner_id": booking.owner_id,
                "user_name": getattr(user, "full_name", None),
                "user_email": getattr(user, "email", None),
                "vehicle_name": getattr(post, "post_title", None),
                "total_price": float(booking.total_price or 0),
                "status": booking.status,
                "start_date": booking.start_date,
                "end_date": booking.end_date,
                "created_at": booking.created_at,
            }
            for booking, user, post in recent_bookings_raw
        ],
        "recent_posts": [
            {
                "id": post.id,
                "owner_id": post.owner_id,
                "owner_name": getattr(owner, "full_name", None),
                "owner_email": getattr(owner, "email", None),
                "post_title": post.post_title,
                "location": post.location,
                "price_per_day": float(post.price_per_day),
                "created_at": post.created_at,
            }
            for post, owner in recent_posts_raw
        ],
        "recent_contacts": [
            {
                "id": contact.id,
                "full_name": contact.full_name,
                "email": contact.email,
                "subject": contact.subject,
                "topic": contact.topic,
                "created_at": contact.created_at,
            }
            for contact in recent_contacts
        ],
    }


def get_pending_driver_licenses(
    db: Session,
    skip: int = 0,
    limit: int = 50,
):
    """Get all pending driver license verifications"""
    licenses = (
        db.query(DriverLicense, User)
        .outerjoin(User, DriverLicense.user_id == User.id)
        .filter(DriverLicense.verification_status == "pending")
        .order_by(DriverLicense.created_at.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    return [
        {
            "id": license.id,
            "user_id": license.user_id,
            "user_name": getattr(user, "full_name", None),
            "user_email": getattr(user, "email", None),
            "user_phone": getattr(user, "phone", None),
            "license_number": license.license_number,
            "license_image_url": license.license_image_url,
            "license_expiry_date": license.license_expiry_date,
            "verification_status": license.verification_status,
            "created_at": license.created_at,
        }
        for license, user in licenses
    ]


def get_all_driver_licenses(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
):
    """Get all driver licenses with optional status filter"""
    query = db.query(DriverLicense, User).outerjoin(User, DriverLicense.user_id == User.id)
    
    if status and status in ["pending", "verified", "rejected"]:
        query = query.filter(DriverLicense.verification_status == status)
    
    licenses = (
        query
        .order_by(DriverLicense.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    return [
        {
            "id": license.id,
            "user_id": license.user_id,
            "user_name": getattr(user, "full_name", None),
            "user_email": getattr(user, "email", None),
            "user_phone": getattr(user, "phone", None),
            "license_number": license.license_number,
            "license_image_url": license.license_image_url,
            "license_expiry_date": license.license_expiry_date,
            "verification_status": license.verification_status,
            "rejection_reason": license.rejection_reason,
            "verified_at": license.verified_at,
            "created_at": license.created_at,
        }
        for license, user in licenses
    ]


def verify_driver_license(
    db: Session,
    license_id: int,
    admin_id: int,
):
    """Mark a driver license as verified"""
    license = db.query(DriverLicense).filter(DriverLicense.id == license_id).first()
    if not license:
        return None
    
    license.verification_status = "verified"
    license.verified_at = datetime.utcnow()
    license.verified_by_admin_id = admin_id
    db.commit()
    db.refresh(license)
    
    # Also update the user's is_active status if needed
    user = db.query(User).filter(User.id == license.user_id).first()
    if user and not user.is_active:
        user.is_active = True
        db.commit()
    
    return {
        "id": license.id,
        "user_id": license.user_id,
        "verification_status": license.verification_status,
        "verified_at": license.verified_at,
    }


def reject_driver_license(
    db: Session,
    license_id: int,
    admin_id: int,
    rejection_reason: str,
):
    """Mark a driver license as rejected"""
    license = db.query(DriverLicense).filter(DriverLicense.id == license_id).first()
    if not license:
        return None
    
    license.verification_status = "rejected"
    license.rejection_reason = rejection_reason
    license.verified_at = datetime.utcnow()
    license.verified_by_admin_id = admin_id
    db.commit()
    db.refresh(license)
    
    return {
        "id": license.id,
        "user_id": license.user_id,
        "verification_status": license.verification_status,
        "rejection_reason": license.rejection_reason,
        "verified_at": license.verified_at,
    }
