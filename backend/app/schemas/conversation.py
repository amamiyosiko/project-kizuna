from datetime import datetime
from pydantic import BaseModel
from app.schemas.common import ORMBase


class ConversationCreate(BaseModel):
    store_id: int
    subject: str | None = None
    order_id: int | None = None
    customer_id: int | None = None
    category: str | None = None
    risk_level: str = "low"
    initial_message: str | None = None


class ConversationUpdateStatus(BaseModel):
    status: str


class ConversationOut(ORMBase):
    id: int
    store_id: int | None
    customer_id: int | None
    order_id: int | None
    subject: str | None
    status: str | None
    category: str | None
    risk_level: str | None
    last_message_at: datetime | None
    last_reply_at: datetime | None = None
    created_at: datetime | None
