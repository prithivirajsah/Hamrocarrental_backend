from sqlalchemy import func
from sqlalchemy.orm import Session

from models.booking import Booking
from models.contact import ContactMessage
from models.post import Post
from models.user import User


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
