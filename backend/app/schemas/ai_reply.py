from pydantic import BaseModel
from app.schemas.common import ORMBase


class GenerateReplyRequest(BaseModel):
    conversation_id: int
    message_id: int | None = None
    tone: str = "polite"


class ApproveReplyRequest(BaseModel):
    final_reply_text: str


class AIReplyOut(ORMBase):
    id: int
    conversation_id: int | None
    message_id: int | None
    detected_category: str | None
    detected_intent: str | None
    risk_level: str | None
    ai_reply_text: str
    final_reply_text: str | None
    confidence_score: float | None
    status: str | None


class TicketGenerateReplyRequest(BaseModel):
    message_id: int | None = None
    tone: str = "polite"
    provider: str = "auto"


class TicketAIReplyOut(BaseModel):
    ticket_id: int
    source_message_id: int
    category: str
    detected_intent: str | None = None
    risk_level: str
    confidence_score: float
    recommended_action: str | None = None
    auto_reply_allowed: bool = False
    reason: str | None = None
    tone: str = "polite"
    provider: str = "rule"
    model: str | None = None
    fallback_used: bool = False
    reply_text: str
    source_excerpt: str | None = None
