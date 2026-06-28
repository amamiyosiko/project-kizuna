from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Conversation, Message
from app.schemas.message import MessageCreate, MessageOut

router = APIRouter(prefix="/conversations/{conversation_id}/messages", tags=["messages"])


@router.get("", response_model=list[MessageOut])
def list_messages(conversation_id: int, db: Session = Depends(get_db)):
    return db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.id.asc()).all()


@router.post("", response_model=MessageOut)
def create_message(conversation_id: int, payload: MessageCreate, db: Session = Depends(get_db)):
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="conversation not found")
    now = datetime.utcnow()
    message = Message(conversation_id=conversation_id, **payload.model_dump(), sent_at=now)
    conversation.last_message_at = now
    if payload.sender_type in {"seller", "ai"}:
        conversation.last_reply_at = now
    db.add(message)
    db.commit()
    db.refresh(message)
    return message
