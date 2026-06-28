from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models import Attachment, Conversation, Store, User
from app.schemas.attachment import AttachmentConfirmRequest, AttachmentRead, PresignUploadRequest, PresignUploadResponse
from app.services.storage import build_object_key, create_presigned_put_url, guess_content_type, public_file_url

router = APIRouter(prefix="/attachments", tags=["attachments"])


@router.post("/presign", response_model=PresignUploadResponse)
def presign_upload(payload: PresignUploadRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not settings.S3_BUCKET_NAME:
        raise HTTPException(status_code=500, detail="S3_BUCKET_NAME is not configured")
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
    return attachment


@router.get("/conversation/{conversation_id}", response_model=list[AttachmentRead])
def list_conversation_attachments(conversation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Attachment).filter(Attachment.conversation_id == conversation_id).order_by(Attachment.id.desc()).all()
