from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.classifier import simple_classify
from app.ai.reply_generator import generate_rule_based_reply
from app.core.config import settings
from app.db.session import get_db
from app.models import AIReply, Message
from app.schemas.ai_reply import AIReplyOut, ApproveReplyRequest, GenerateReplyRequest

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/classify")
def classify_text(content: str):
    return simple_classify(content)


@router.post("/generate-reply", response_model=AIReplyOut)
def generate_reply(payload: GenerateReplyRequest, db: Session = Depends(get_db)):
    message = None
    if payload.message_id:
        message = db.query(Message).filter(Message.id == payload.message_id).first()
    else:
        message = db.query(Message).filter(Message.conversation_id == payload.conversation_id).order_by(Message.id.desc()).first()
    if not message:
        raise HTTPException(status_code=404, detail="message not found")

    generated = generate_rule_based_reply(message.content, tone=payload.tone)
    ai_reply = AIReply(
        conversation_id=payload.conversation_id,
        message_id=message.id,
        detected_category=generated["category"],
        detected_intent=generated.get("detected_intent"),
        risk_level=generated["risk_level"],
        ai_reply_text=generated["reply"],
        confidence_score=generated["confidence_score"],
        status="draft",
        model_name=settings.OPENAI_MODEL,
    )
    db.add(ai_reply)
    db.commit()
    db.refresh(ai_reply)
    return ai_reply


@router.post("/approve-reply/{reply_id}", response_model=AIReplyOut)
def approve_reply(reply_id: int, payload: ApproveReplyRequest, db: Session = Depends(get_db)):
    reply = db.query(AIReply).filter(AIReply.id == reply_id).first()
    if not reply:
        raise HTTPException(status_code=404, detail="reply not found")
    reply.final_reply_text = payload.final_reply_text
    reply.status = "approved"
    db.commit()
    db.refresh(reply)
    return reply
