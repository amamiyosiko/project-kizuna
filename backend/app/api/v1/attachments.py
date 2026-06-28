from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models import Attachment, Conversation, Store, Ticket, TicketEvent, TicketMessage, User
from app.schemas.attachment import (
    AttachmentConfirmRequest,
    AttachmentRead,
    PresignUploadRequest,
    PresignUploadResponse,
    TicketAttachmentConfirmRequest,
    TicketPresignUploadRequest,
)
from app.services.storage import (
    build_object_key,
    build_ticket_object_key,
    create_presigned_get_url,
    create_presigned_put_url,
    guess_content_type,
    public_file_url,
)

router = APIRouter(prefix="/attachments", tags=["attachments"])

IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
PREVIEW_TYPES = IMAGE_TYPES | {"application/pdf", "text/plain"}


def _attachment_out(attachment: Attachment) -> AttachmentRead:
    content_type = attachment.content_type or guess_content_type(attachment.file_name)
    can_preview = content_type in PREVIEW_TYPES or content_type.startswith("image/")
    return AttachmentRead(
        id=attachment.id,
        conversation_id=attachment.conversation_id,
        ticket_id=attachment.ticket_id,
        message_id=attachment.message_id,
        ticket_message_id=attachment.ticket_message_id,
        store_id=attachment.store_id,
        file_name=attachment.file_name,
        content_type=content_type,
        file_size=attachment.file_size,
        bucket=attachment.bucket,
        object_key=attachment.object_key,
        status=attachment.status,
        file_url=create_presigned_get_url(attachment.object_key),
        can_preview=can_preview,
        created_at=attachment.created_at,
    )


def _ensure_s3_configured() -> None:
    if not settings.S3_BUCKET_NAME:
        raise HTTPException(status_code=500, detail="S3_BUCKET_NAME is not configured")


def _add_ticket_event(db: Session, ticket_id: int, title: str, description: str, actor: User | None = None) -> None:
    db.add(TicketEvent(
        ticket_id=ticket_id,
        event_type="ATTACHMENT_ADDED",
        title=title,
        description=description,
        actor_type="USER" if actor else "SYSTEM",
        actor_user_id=actor.id if actor else None,
    ))


@router.post("/presign", response_model=PresignUploadResponse)
def presign_upload(payload: PresignUploadRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _ensure_s3_configured()
    conversation = db.query(Conversation).filter(Conversation.id == payload.conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    store = db.query(Store).filter(Store.id == conversation.store_id).first() if conversation.store_id else None
    store_code = store.store_code if store else "unknown-store"
    content_type = payload.content_type or guess_content_type(payload.file_name)
    object_key = build_object_key(store_code=store_code, conversation_id=payload.conversation_id, file_name=payload.file_name)
    upload_url = create_presigned_put_url(object_key, content_type)
    return PresignUploadResponse(
        upload_url=upload_url,
        bucket=settings.S3_BUCKET_NAME,
        object_key=object_key,
        file_url=public_file_url(object_key),
        expires_seconds=settings.S3_UPLOAD_EXPIRES_SECONDS,
    )


@router.post("/confirm", response_model=AttachmentRead)
def confirm_upload(payload: AttachmentConfirmRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    conversation = db.query(Conversation).filter(Conversation.id == payload.conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    ext = Path(payload.file_name).suffix.lower().lstrip(".")
    attachment = Attachment(
        conversation_id=payload.conversation_id,
        message_id=payload.message_id,
        store_id=conversation.store_id,
        file_name=payload.file_name,
        file_ext=ext,
        content_type=payload.content_type,
        file_size=payload.file_size,
        bucket=payload.bucket,
        object_key=payload.object_key,
        status="uploaded",
        uploaded_by=current_user.id,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return _attachment_out(attachment)


@router.get("/conversation/{conversation_id}", response_model=list[AttachmentRead])
def list_conversation_attachments(conversation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = db.query(Attachment).filter(Attachment.conversation_id == conversation_id).order_by(Attachment.id.desc()).all()
    return [_attachment_out(row) for row in rows]


@router.post("/tickets/{ticket_id}/presign", response_model=PresignUploadResponse)
def presign_ticket_upload(ticket_id: int, payload: TicketPresignUploadRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _ensure_s3_configured()
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="ticket not found")
    store = db.query(Store).filter(Store.id == ticket.store_id).first() if ticket.store_id else None
    store_code = store.store_code if store else "unknown-store"
    content_type = payload.content_type or guess_content_type(payload.file_name)
    object_key = build_ticket_object_key(store_code=store_code, ticket_id=ticket.id, ticket_no=ticket.ticket_no, file_name=payload.file_name)
    upload_url = create_presigned_put_url(object_key, content_type)
    return PresignUploadResponse(
        upload_url=upload_url,
        bucket=settings.S3_BUCKET_NAME,
        object_key=object_key,
        file_url=public_file_url(object_key),
        expires_seconds=settings.S3_UPLOAD_EXPIRES_SECONDS,
    )


@router.post("/tickets/{ticket_id}/confirm", response_model=AttachmentRead)
def confirm_ticket_upload(ticket_id: int, payload: TicketAttachmentConfirmRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="ticket not found")
    ticket_message = None
    if payload.ticket_message_id:
        ticket_message = db.query(TicketMessage).filter(TicketMessage.id == payload.ticket_message_id, TicketMessage.ticket_id == ticket_id).first()
        if not ticket_message:
            raise HTTPException(status_code=404, detail="ticket message not found")

    ext = Path(payload.file_name).suffix.lower().lstrip(".")
    attachment = Attachment(
        ticket_id=ticket.id,
        ticket_message_id=ticket_message.id if ticket_message else None,
        store_id=ticket.store_id,
        file_name=payload.file_name,
        file_ext=ext,
        content_type=payload.content_type,
        file_size=payload.file_size,
        bucket=payload.bucket,
        object_key=payload.object_key,
        status="uploaded",
        uploaded_by=current_user.id,
    )
    db.add(attachment)
    _add_ticket_event(db, ticket.id, "附件已上传", f"{payload.file_name}（{payload.file_size or 0} bytes）", current_user)
    db.commit()
    db.refresh(attachment)
    return _attachment_out(attachment)


@router.get("/tickets/{ticket_id}", response_model=list[AttachmentRead])
def list_ticket_attachments(ticket_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not db.query(Ticket.id).filter(Ticket.id == ticket_id).first():
        raise HTTPException(status_code=404, detail="ticket not found")
    rows = db.query(Attachment).filter(Attachment.ticket_id == ticket_id).order_by(Attachment.id.desc()).all()
    return [_attachment_out(row) for row in rows]


@router.get("/{attachment_id}", response_model=AttachmentRead)
def get_attachment(attachment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="attachment not found")
    return _attachment_out(attachment)
