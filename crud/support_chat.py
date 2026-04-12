from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from models.support_conversation import SupportConversation
from models.support_message import SupportMessage
from models.user import User


def create_support_conversation(db: Session, user_id: int) -> SupportConversation:
    conversation = SupportConversation(user_id=user_id, is_open=True)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def get_support_conversation_by_id(db: Session, conversation_id: int) -> Optional[SupportConversation]:
    return (
        db.query(SupportConversation)
        .filter(SupportConversation.id == conversation_id)
        .first()
    )


def get_user_support_conversations(db: Session, user_id: int) -> list[SupportConversation]:
    return (
        db.query(SupportConversation)
        .filter(SupportConversation.user_id == user_id)
        .order_by(SupportConversation.updated_at.desc(), SupportConversation.id.desc())
        .all()
    )


def get_latest_open_support_conversation_for_user(db: Session, user_id: int) -> Optional[SupportConversation]:
    return (
        db.query(SupportConversation)
        .filter(SupportConversation.user_id == user_id, SupportConversation.is_open.is_(True))
        .order_by(SupportConversation.updated_at.desc(), SupportConversation.id.desc())
        .first()
    )


def get_admin_support_conversations(db: Session) -> list[SupportConversation]:
    return (
        db.query(SupportConversation)
        .order_by(SupportConversation.updated_at.desc(), SupportConversation.id.desc())
        .all()
    )


def get_support_messages(db: Session, conversation_id: int) -> list[SupportMessage]:
    return (
        db.query(SupportMessage)
        .filter(SupportMessage.conversation_id == conversation_id)
        .order_by(SupportMessage.created_at.asc(), SupportMessage.id.asc())
        .all()
    )


def create_support_message(
    db: Session,
    conversation_id: int,
    sender_id: int,
    message: str,
) -> SupportMessage:
    support_message = SupportMessage(
        conversation_id=conversation_id,
        sender_id=sender_id,
        message=message,
        is_read=False,
    )
    db.add(support_message)

    conversation = get_support_conversation_by_id(db, conversation_id)
    if conversation:
        conversation.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(support_message)
    return support_message


def mark_conversation_as_read_for_user(
    db: Session,
    conversation_id: int,
    user_id: int,
) -> int:
    messages_to_mark = (
        db.query(SupportMessage)
        .filter(
            SupportMessage.conversation_id == conversation_id,
            SupportMessage.sender_id != user_id,
            SupportMessage.is_read.is_(False),
        )
        .all()
    )

    for item in messages_to_mark:
        item.is_read = True

    if messages_to_mark:
        db.commit()

    return len(messages_to_mark)


def get_latest_support_message(db: Session, conversation_id: int) -> Optional[SupportMessage]:
    return (
        db.query(SupportMessage)
        .filter(SupportMessage.conversation_id == conversation_id)
        .order_by(SupportMessage.created_at.desc(), SupportMessage.id.desc())
        .first()
    )


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_unread_count_for_admin(db: Session, conversation_id: int) -> int:
    return (
        db.query(SupportMessage)
        .join(User, User.id == SupportMessage.sender_id)
        .filter(
            SupportMessage.conversation_id == conversation_id,
            SupportMessage.is_read.is_(False),
            User.role == "user",
        )
        .count()
    )


def get_unread_count_for_user(db: Session, conversation_id: int) -> int:
    return (
        db.query(SupportMessage)
        .join(User, User.id == SupportMessage.sender_id)
        .filter(
            SupportMessage.conversation_id == conversation_id,
            SupportMessage.is_read.is_(False),
            User.role == "admin",
        )
        .count()
    )
