from datetime import datetime
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.kyc_document import KycDocument
from models.user import User


def create_kyc_document(
    db: Session,
    user_id: int,
    document_type: str,
    document_number: str,
    front_image_url: str,
    back_image_url: Optional[str] = None,
    front_image_data: Optional[bytes] = None,
    front_image_content_type: Optional[str] = None,
    front_image_filename: Optional[str] = None,
    back_image_data: Optional[bytes] = None,
    back_image_content_type: Optional[str] = None,
    back_image_filename: Optional[str] = None,
):
    document = KycDocument(
        user_id=user_id,
        document_type=document_type,
        document_number=document_number,
        front_image_url=front_image_url,
        front_image_data=front_image_data,
        front_image_content_type=front_image_content_type,
        front_image_filename=front_image_filename,
        back_image_url=back_image_url,
        back_image_data=back_image_data,
        back_image_content_type=back_image_content_type,
        back_image_filename=back_image_filename,
        verification_status="pending",
    )
    db.add(document)
    try:
        db.commit()
    except IntegrityError as exc:
        # Backward compatibility for databases that still have NOT NULL on back_image_url.
        db.rollback()
        if "back_image_url" not in str(exc):
            raise
        document = KycDocument(
            user_id=user_id,
            document_type=document_type,
            document_number=document_number,
            front_image_url=front_image_url,
            front_image_data=front_image_data,
            front_image_content_type=front_image_content_type,
            front_image_filename=front_image_filename,
            back_image_url=back_image_url or front_image_url,
            back_image_data=back_image_data,
            back_image_content_type=back_image_content_type,
            back_image_filename=back_image_filename,
            verification_status="pending",
        )
        db.add(document)
        db.commit()
    db.refresh(document)
    return document


def get_latest_user_kyc_document(db: Session, user_id: int):
    return (
        db.query(KycDocument)
        .filter(KycDocument.user_id == user_id)
        .order_by(KycDocument.created_at.desc(), KycDocument.id.desc())
        .first()
    )


def get_admin_kyc_documents(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    search: Optional[str] = None,
):
    query = db.query(KycDocument, User).outerjoin(User, KycDocument.user_id == User.id)

    normalized_status = (status or "").strip().lower()
    if normalized_status in {"pending", "approved", "rejected"}:
        query = query.filter(KycDocument.verification_status == normalized_status)

    normalized_search = (search or "").strip().lower()
    if normalized_search:
        like = f"%{normalized_search}%"
        query = query.filter(
            User.full_name.ilike(like)
            | User.email.ilike(like)
            | KycDocument.document_type.ilike(like)
            | KycDocument.document_number.ilike(like)
        )

    rows = (
        query
        .order_by(KycDocument.created_at.desc(), KycDocument.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        {
            "id": doc.id,
            "user_id": doc.user_id,
            "user_name": getattr(user, "full_name", None),
            "user_email": getattr(user, "email", None),
            "document_type": doc.document_type,
            "document_number": doc.document_number,
            "front_image_url": doc.front_image_url,
            "back_image_url": doc.back_image_url,
            "verification_status": doc.verification_status,
            "rejection_reason": doc.rejection_reason,
            "reviewed_at": doc.reviewed_at,
            "created_at": doc.created_at,
        }
        for doc, user in rows
    ]


def update_kyc_status(
    db: Session,
    document_id: int,
    admin_id: int,
    status: str,
    rejection_reason: Optional[str] = None,
):
    document = db.query(KycDocument).filter(KycDocument.id == document_id).first()
    if not document:
        return None

    document.verification_status = status
    document.rejection_reason = rejection_reason if status == "rejected" else None
    document.reviewed_by_admin_id = admin_id
    document.reviewed_at = datetime.utcnow()

    db.commit()
    db.refresh(document)
    return {
        "id": document.id,
        "verification_status": document.verification_status,
        "rejection_reason": document.rejection_reason,
        "reviewed_at": document.reviewed_at,
    }
