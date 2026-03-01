from typing import List
from pydantic import BaseModel


class HomeFeature(BaseModel):
    title: str
    description: str
    icon: str


class HomeStat(BaseModel):
    label: str
    value: str


class FeaturedVehicle(BaseModel):
    id: int
    name: str
    category: str
    price_per_day: int
    currency: str
    location: str
    rating: float
    image_url: str
    is_available: bool


class HomePageResponse(BaseModel):
    message: str
    hero_title: str
    hero_subtitle: str
    search_placeholder: str
    features: List[HomeFeature]
    stats: List[HomeStat]
    featured_vehicles: List[FeaturedVehicle]
    cta_text: str
