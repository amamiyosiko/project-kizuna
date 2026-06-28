from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import AIReply, Conversation, Message, Store

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    return {
        "stores": db.query(Store).count(),
        "conversations": db.query(Conversation).count(),
        "messages": db.query(Message).count(),
        "ai_replies": db.query(AIReply).count(),
        "open_conversations": db.query(Conversation).filter(Conversation.status == "open").count(),
        "pending_conversations": db.query(Conversation).filter(Conversation.status == "pending").count(),
    }
