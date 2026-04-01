from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.sql import func

from database_connection import Base


class KycDocument(Base):
    __tablename__ = "kyc_documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    document_type = Column(String, nullable=False)
    document_number = Column(String, nullable=False)
    front_image_url = Column(String, nullable=False)
    front_image_data = Column(LargeBinary, nullable=True)
    front_image_content_type = Column(String, nullable=True)
    front_image_filename = Column(String, nullable=True)
    back_image_url = Column(String, nullable=True)
    back_image_data = Column(LargeBinary, nullable=True)
    back_image_content_type = Column(String, nullable=True)
    back_image_filename = Column(String, nullable=True)
    verification_status = Column(
        Enum("pending", "approved", "rejected", name="kyc_verification_status"),
        nullable=False,
        default="pending",
        index=True,
    )
    rejection_reason = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by_admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
