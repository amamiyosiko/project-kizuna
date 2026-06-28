from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.classifier import simple_classify
from app.ai.providers import AIContext, generate_ai_customer_reply
from app.ai.reply_generator import generate_rule_based_reply
from app.core.config import settings
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import AIReply, Message, Ticket, TicketEvent, TicketMessage, User
from app.schemas.ai_reply import (
    AIReplyOut,
    ApproveReplyRequest,
    GenerateReplyRequest,
    TicketAIReplyOut,
    TicketGenerateReplyRequest,
)

router = APIRouter(prefix="/ai", tags=["ai"])


def _add_ticket_event(
    db: Session,
    ticket_id: int,
    event_type: str,
    title: str,
    description: str | None = None,
    actor: User | None = None,
) -> None:
    db.add(TicketEvent(
        ticket_id=ticket_id,
        event_type=event_type,
        title=title,
        description=description,
        actor_type="USER" if actor else "SYSTEM",
        actor_user_id=actor.id if actor else None,
    ))


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


@router.post("/tickets/{ticket_id}/generate-reply", response_model=TicketAIReplyOut)
def generate_ticket_reply(
    ticket_id: int,
    payload: TicketGenerateReplyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a Japanese draft reply for a work item.

    v0.3.3.1 keeps the workflow safe and deterministic: AI produces a draft and
    analysis, but it does not send anything to Amazon. The agent can copy the
    draft into the reply box, edit it, and save it to the ticket timeline.
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="ticket not found")

    source_query = db.query(TicketMessage).filter(TicketMessage.ticket_id == ticket.id)
    if payload.message_id:
        source_query = source_query.filter(TicketMessage.id == payload.message_id)
    else:
        source_query = source_query.filter(TicketMessage.sender_type == "CUSTOMER")

    source_message = source_query.order_by(TicketMessage.id.desc()).first()
    if not source_message:
        raise HTTPException(status_code=404, detail="customer message not found")

    generated = generate_ai_customer_reply(
        source_message.content,
        tone=payload.tone,
        provider=payload.provider,
        context=AIContext(
            ticket_no=ticket.ticket_no,
            buyer_name=ticket.buyer_name,
            order_no=ticket.order_no,
            asin=ticket.asin,
            sku=ticket.sku,
            subject=ticket.subject,
            category=ticket.category,
            risk_level=ticket.risk_level,
        ),
    )
    description = (
        f"Provider：{generated.get('provider')} / 模型：{generated.get('model')} / "
        f"分类：{generated['category']} / 风险：{generated['risk_level']} / "
        f"可信度：{generated['confidence_score']}%"
    )
    if generated.get("fallback_used"):
        description += " / 已使用备用规则"
    _add_ticket_event(db, ticket.id, "AI_REPLY_GENERATED", "AI 回复草稿已生成", description, current_user)
    db.commit()

    return TicketAIReplyOut(
        ticket_id=ticket.id,
        source_message_id=source_message.id,
        category=generated["category"],
        detected_intent=generated.get("detected_intent"),
        risk_level=generated["risk_level"],
        confidence_score=float(generated["confidence_score"] or 0),
        recommended_action=generated.get("recommended_action"),
        auto_reply_allowed=bool(generated.get("auto_reply_allowed")),
        reason=generated.get("reason"),
        tone=generated.get("tone") or payload.tone,
        provider=generated.get("provider") or "rule",
        model=generated.get("model"),
        fallback_used=bool(generated.get("fallback_used")),
        reply_text=generated["reply"],
        source_excerpt=(source_message.content or "")[:300],
    )
