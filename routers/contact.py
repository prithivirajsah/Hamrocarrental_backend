from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from flask_jwt_extended import jwt_required
from database_connection import get_db
from crud.contact import create_contact_message
from schemas.contact import ContactMessageCreate, ContactSubmitResponse


router = APIRouter(prefix="/contact", tags=["Contact"])


@router.post("", response_model=ContactSubmitResponse, status_code=status.HTTP_201_CREATED)
#$check authentication and token
@jwt_required()
def submit_contact_form(payload: ContactMessageCreate, db: Session = Depends(get_db)):
    contact = create_contact_message(db, payload)
    return {
        "message": "Your message has been sent successfully.",
        "contact": contact,
    }
