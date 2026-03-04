from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func

from database_connection import Base


class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False, index=True)
    subject = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    phone_number = Column(String, nullable=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
