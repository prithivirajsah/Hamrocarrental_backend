from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from crud.user import count_users_by_role
from database_connection import get_db
from schemas.home import HomePageResponse

router = APIRouter(tags=["Home"])


@router.get("/home", response_model=HomePageResponse)
def get_home_page(db: Session = Depends(get_db)):
    role_counts = count_users_by_role(db)
    total_users = sum(role_counts.values())
    total_drivers = role_counts.get("driver", 0)
    total_customers = role_counts.get("user", 0)

    return {
        "message": "Home page backend data fetched successfully",
        "hero_title": "Find Your Perfect Rental Car in Nepal",
        "hero_subtitle": "Affordable daily rentals, verified drivers, and quick booking support.",
        "search_placeholder": "Search by city, vehicle type, or budget",
        "features": [
            {
                "title": "Wide Vehicle Selection",
                "description": "Choose from hatchbacks, SUVs, vans, and premium cars.",
                "icon": "car",
            },
            {
                "title": "Verified Drivers",
                "description": "Book with confidence from verified and active drivers.",
                "icon": "user-check",
            },
            {
                "title": "Secure Booking",
                "description": "Fast and reliable booking flow with support when needed.",
                "icon": "shield-check",
            },
        ],
        "stats": [
            {"label": "Registered Users", "value": str(total_users)},
            {"label": "Available Drivers", "value": str(total_drivers)},
            {"label": "Happy Customers", "value": str(total_customers)},
        ],
        "featured_vehicles": [
            {
                "id": 1,
                "name": "Hyundai i20",
                "category": "Hatchback",
                "price_per_day": 4200,
                "currency": "NPR",
                "location": "Kathmandu",
                "rating": 4.7,
                "image_url": "https://images.unsplash.com/photo-1549924231-f129b911e442",
                "is_available": True,
            },
            {
                "id": 2,
                "name": "Toyota Hilux",
                "category": "Pickup",
                "price_per_day": 7800,
                "currency": "NPR",
                "location": "Pokhara",
                "rating": 4.8,
                "image_url": "https://images.unsplash.com/photo-1503376780353-7e6692767b70",
                "is_available": True,
            },
            {
                "id": 3,
                "name": "Mahindra Scorpio",
                "category": "SUV",
                "price_per_day": 6800,
                "currency": "NPR",
                "location": "Lalitpur",
                "rating": 4.6,
                "image_url": "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7",
                "is_available": False,
            },
        ],
        "cta_text": "Book your next ride with HamroRental today.",
    }
