from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Conversation, Message
from app.schemas.conversation import ConversationCreate, ConversationOut, ConversationUpdateStatus

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationOut])
def list_conversations(
    store_id: int | None = None,
    status: str | None = None,
    category: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Conversation)
    if store_id:
        query = query.filter(Conversation.store_id == store_id)
    if status:
        query = query.filter(Conversation.status == status)
    if category:
        query = query.filter(Conversation.category == category)
    return query.order_by(Conversation.last_message_at.desc().nullslast(), Conversation.id.desc()).all()


@router.post("", response_model=ConversationOut)
def create_conversation(payload: ConversationCreate, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude={"initial_message"})
    conversation = Conversation(**data, status="open", last_message_at=datetime.utcnow())
    db.add(conversation)
    db.flush()
    if payload.initial_message:
        db.add(Message(
            conversation_id=conversation.id,
            sender_type="buyer",
            message_type="text",
            content=payload.initial_message,
            original_language="ja",
            sent_at=datetime.utcnow(),
        ))
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("/{conversation_id}", response_model=ConversationOut)
def get_conversation(conversation_id: int, db: Session = Depends(get_db)):
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="conversation not found")
    return conversation


@router.put("/{conversation_id}/status", response_model=ConversationOut)
def update_status(conversation_id: int, payload: ConversationUpdateStatus, db: Session = Depends(get_db)):
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="conversation not found")
    allowed = {"open", "processing", "waiting_customer", "done", "closed"}
    if payload.status not in allowed:
        raise HTTPException(status_code=400, detail="invalid status")
    conversation.status = payload.status
    if payload.status in {"done", "closed"}:
        conversation.last_reply_at = datetime.utcnow()
    db.commit()
    db.refresh(conversation)
    return conversation
