from datetime import datetime
from pydantic import BaseModel
from app.schemas.common import ORMBase


class MessageCreate(BaseModel):
    sender_type: str = "buyer"
    message_type: str = "text"
    content: str
    original_language: str = "ja"


class MessageOut(ORMBase):
    id: int
    conversation_id: int | None
    sender_type: str
    message_type: str | None
    content: str
    original_language: str | None
    has_attachment: bool | None
    sent_at: datetime | None
    created_at: datetime | None
