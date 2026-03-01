from sqlalchemy import Column, Integer, String, Date, DateTime, Enum, ForeignKey
from sqlalchemy.sql import func

from database_connection import Base


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    vehicle_type = Column(String, nullable=False, index=True)
    pickup_location = Column(String, nullable=False, index=True)
    dropoff_location = Column(String, nullable=False, index=True)
    pickup_date = Column(Date, nullable=False, index=True)
    return_date = Column(Date, nullable=False, index=True)
    status = Column(
        Enum("pending", "confirmed", "cancelled", "completed", name="booking_status"),
        nullable=False,
        default="pending",
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
