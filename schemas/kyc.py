from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class KycDocumentOut(BaseModel):
    id: int
    user_id: int
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    document_type: str
    document_number: str
    front_image_url: str
    back_image_url: Optional[str] = None
    verification_status: str
    rejection_reason: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime


class KycStatusUpdateRequest(BaseModel):
    status: str
    rejection_reason: Optional[str] = None


class KycStatusUpdateResponse(BaseModel):
    id: int
    verification_status: str
    rejection_reason: Optional[str] = None
    reviewed_at: Optional[datetime] = None
