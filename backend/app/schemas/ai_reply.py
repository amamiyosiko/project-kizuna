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
