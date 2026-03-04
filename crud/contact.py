from sqlalchemy.orm import Session

from models.contact import ContactMessage
from schemas.contact import ContactMessageCreate


def create_contact_message(db: Session, payload: ContactMessageCreate) -> ContactMessage:
    db_contact = ContactMessage(
        full_name=payload.full_name,
        email=payload.email.lower(),
        subject=payload.subject,
        topic=payload.topic,
        phone_number=payload.phone_number,
        message=payload.message,
    )
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact
