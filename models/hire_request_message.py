from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.sql import func

from database_connection import Base


class HireRequestMessage(Base):
    __tablename__ = "hire_request_messages"

    id = Column(Integer, primary_key=True, index=True)
    hire_request_id = Column(Integer, ForeignKey("hire_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
