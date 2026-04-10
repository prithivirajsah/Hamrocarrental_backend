from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session
from flask_jwt_extended import jwt_required
from database_connection import get_db
from crud.contact import create_contact_message
from schemas.contact import ContactMessageCreate, ContactSubmitResponse
from utils.email_service import send_contact_received_email, send_contact_notification_email


router = APIRouter(prefix="/contact", tags=["Contact"])


@router.post("", response_model=ContactSubmitResponse, status_code=status.HTTP_201_CREATED)
#$check authentication and token
@jwt_required()
def submit_contact_form(
    payload: ContactMessageCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    contact = create_contact_message(db, payload)
    background_tasks.add_task(send_contact_received_email, contact)
    background_tasks.add_task(send_contact_notification_email, contact)
    return {
        "message": "Your message has been sent successfully.",
        "contact": contact,
    }
