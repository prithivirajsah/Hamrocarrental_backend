from sqlalchemy import Column, Integer, String, DateTime, Text, Float, JSON, ForeignKey
from sqlalchemy.sql import func

from database_connection import Base


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    post_title = Column(String, nullable=False)
    category = Column(String, nullable=False, default="sedan", index=True)
    price_per_day = Column(Float, nullable=False)
    location = Column(String, nullable=False)
    contact_number = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    features = Column(JSON, nullable=False, default=list)
    image_urls = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
