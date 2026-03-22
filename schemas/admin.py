from datetime import date, datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_users: int
    total_admins: int
    total_drivers: int
    total_posts: int
    total_bookings: int
    pending_bookings: int
    confirmed_bookings: int
    completed_bookings: int
    cancelled_bookings: int
    total_revenue: float


class DashboardBookingItem(BaseModel):
    id: int
    user_id: int
    owner_id: int
    post_id: int
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    vehicle_name: Optional[str] = None
    total_price: float
    status: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    created_at: datetime


class DashboardPostItem(BaseModel):
    id: int
    owner_id: int
    owner_name: Optional[str] = None
    owner_email: Optional[str] = None
    post_title: str
    location: str
    price_per_day: float
    created_at: datetime


class AdminPostListItem(BaseModel):
    id: int
    owner_id: int
    owner_name: Optional[str] = None
    owner_email: Optional[str] = None
    owner_role: Optional[str] = None
    post_title: str
    category: str
    price_per_day: float
    location: str
    contact_number: str
    description: str
    features: List[str]
    image_urls: List[str]
    created_at: datetime


class DashboardContactItem(BaseModel):
    id: int
    full_name: str
    email: str
    subject: str
    topic: str
    created_at: datetime


class AdminDashboardResponse(BaseModel):
    stats: DashboardStats
    booking_status_breakdown: Dict[str, int]
    recent_bookings: List[DashboardBookingItem]
    recent_posts: List[DashboardPostItem]
    recent_contacts: List[DashboardContactItem]
