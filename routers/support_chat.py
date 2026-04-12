from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth.jwt import get_current_user, is_admin_user
from crud.support_chat import (
    create_support_conversation,
    create_support_message,
    get_admin_support_conversations,
    get_latest_open_support_conversation_for_user,
    get_latest_support_message,
    get_support_conversation_by_id,
    get_support_messages,
    get_unread_count_for_admin,
    get_unread_count_for_user,
    get_user_by_id,
    get_user_support_conversations,
    mark_conversation_as_read_for_user,
)
from database_connection import get_db
from schemas.support_chat import (
    SupportConversationCreate,
    SupportConversationDetailOut,
    SupportConversationSummaryOut,
    SupportMessageCreate,
    SupportMessageOut,
    SupportReadReceiptOut,
)

router = APIRouter(prefix="/support-chat", tags=["Support Chat"])


def _ensure_normal_user(current_user):
    if current_user.role != "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only users can access this endpoint",
        )


def _ensure_admin(current_user):
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


def _to_message_out(db: Session, message) -> SupportMessageOut:
    sender = get_user_by_id(db, message.sender_id)
    return SupportMessageOut(
        id=message.id,
        conversation_id=message.conversation_id,
        sender_id=message.sender_id,
        sender_name=getattr(sender, "full_name", None),
        sender_email=getattr(sender, "email", None),
        sender_role=getattr(sender, "role", None),
        message=message.message,
        is_read=message.is_read,
        created_at=message.created_at,
    )


def _to_conversation_summary_out(db: Session, conversation) -> SupportConversationSummaryOut:
    user = get_user_by_id(db, conversation.user_id)
    latest_message = get_latest_support_message(db, conversation.id)
    return SupportConversationSummaryOut(
        id=conversation.id,
        user_id=conversation.user_id,
        user_name=getattr(user, "full_name", None),
        user_email=getattr(user, "email", None),
        is_open=conversation.is_open,
        unread_count_for_admin=get_unread_count_for_admin(db, conversation.id),
        unread_count_for_user=get_unread_count_for_user(db, conversation.id),
        last_message=_to_message_out(db, latest_message) if latest_message else None,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


def _ensure_conversation_access(conversation, current_user):
    if is_admin_user(current_user):
        return

    if conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this conversation",
        )


@router.post(
    "/conversations/me/active",
    response_model=SupportConversationSummaryOut,
    status_code=status.HTTP_200_OK,
)
def get_or_create_my_active_conversation(
    payload: SupportConversationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_normal_user(current_user)

    conversation = None
    if not payload.create_new:
        conversation = get_latest_open_support_conversation_for_user(db, current_user.id)

    if not conversation:
        conversation = create_support_conversation(db, user_id=current_user.id)

    return _to_conversation_summary_out(db, conversation)


@router.get(
    "/conversations/me",
    response_model=list[SupportConversationSummaryOut],
    status_code=status.HTTP_200_OK,
)
def list_my_support_conversations(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_normal_user(current_user)
    conversations = get_user_support_conversations(db, current_user.id)
    return [_to_conversation_summary_out(db, item) for item in conversations]


@router.get(
    "/admin/conversations",
    response_model=list[SupportConversationSummaryOut],
    status_code=status.HTTP_200_OK,
)
def list_admin_support_conversations(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_admin(current_user)
    conversations = get_admin_support_conversations(db)
    return [_to_conversation_summary_out(db, item) for item in conversations]


@router.get(
    "/admin/conversations/{conversation_id}/messages",
    response_model=list[SupportMessageOut],
    status_code=status.HTTP_200_OK,
)
def list_admin_support_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_admin(current_user)

    conversation = get_support_conversation_by_id(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    messages = get_support_messages(db, conversation_id)
    return [_to_message_out(db, item) for item in messages]


@router.post(
    "/admin/conversations/{conversation_id}/messages",
    response_model=SupportMessageOut,
    status_code=status.HTTP_201_CREATED,
)
def send_admin_support_message(
    conversation_id: int,
    payload: SupportMessageCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_admin(current_user)

    conversation = get_support_conversation_by_id(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    support_message = create_support_message(
        db,
        conversation_id=conversation.id,
        sender_id=current_user.id,
        message=payload.message,
    )
    return _to_message_out(db, support_message)


@router.patch(
    "/admin/conversations/{conversation_id}/read",
    response_model=SupportReadReceiptOut,
    status_code=status.HTTP_200_OK,
)
def mark_admin_support_messages_as_read(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_admin(current_user)

    conversation = get_support_conversation_by_id(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    marked_count = mark_conversation_as_read_for_user(db, conversation_id, current_user.id)
    return SupportReadReceiptOut(conversation_id=conversation_id, marked_count=marked_count)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[SupportMessageOut],
    status_code=status.HTTP_200_OK,
)
def list_support_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    conversation = get_support_conversation_by_id(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    _ensure_conversation_access(conversation, current_user)
    messages = get_support_messages(db, conversation_id)
    return [_to_message_out(db, item) for item in messages]


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=SupportMessageOut,
    status_code=status.HTTP_201_CREATED,
)
def send_support_message(
    conversation_id: int,
    payload: SupportMessageCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    conversation = get_support_conversation_by_id(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    _ensure_conversation_access(conversation, current_user)

    support_message = create_support_message(
        db,
        conversation_id=conversation.id,
        sender_id=current_user.id,
        message=payload.message,
    )
    return _to_message_out(db, support_message)


@router.patch(
    "/conversations/{conversation_id}/read",
    response_model=SupportReadReceiptOut,
    status_code=status.HTTP_200_OK,
)
def mark_support_messages_as_read(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    conversation = get_support_conversation_by_id(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    _ensure_conversation_access(conversation, current_user)
    marked_count = mark_conversation_as_read_for_user(db, conversation_id, current_user.id)
    return SupportReadReceiptOut(conversation_id=conversation_id, marked_count=marked_count)


@router.get(
    "/conversations/{conversation_id}",
    response_model=SupportConversationDetailOut,
    status_code=status.HTTP_200_OK,
)
def get_support_conversation_detail(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    conversation = get_support_conversation_by_id(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    _ensure_conversation_access(conversation, current_user)

    messages = get_support_messages(db, conversation.id)
    return SupportConversationDetailOut(
        conversation=_to_conversation_summary_out(db, conversation),
        messages=[_to_message_out(db, item) for item in messages],
    )
