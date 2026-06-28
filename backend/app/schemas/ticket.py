from datetime import datetime
from pydantic import BaseModel
from app.schemas.common import ORMBase


class TicketCreate(BaseModel):
    store_id: int
    buyer_name: str
    buyer_id: str | None = None
    order_no: str | None = None
    asin: str | None = None
    sku: str | None = None
    subject: str | None = None
    category: str | None = None
    priority: str = "P3"
    risk_level: str = "low"
    initial_message: str


class TicketUpdate(BaseModel):
    status: str | None = None
    priority: str | None = None
    category: str | None = None
    risk_level: str | None = None
    assigned_user_id: int | None = None
    subject: str | None = None
    order_no: str | None = None
    asin: str | None = None
    sku: str | None = None


class TicketOut(ORMBase):
    id: int
    ticket_no: str
    platform: str | None = None
    marketplace: str | None = None
    store_id: int | None = None
    buyer_name: str
    buyer_id: str | None = None
    order_no: str | None = None
    asin: str | None = None
    sku: str | None = None
    subject: str | None = None
    status: str | None = None
    priority: str | None = None
    category: str | None = None
    risk_level: str | None = None
    language: str | None = None
    assigned_user_id: int | None = None
    last_message_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TicketMessageCreate(BaseModel):
    sender_type: str
    content: str
    message_type: str = "text"


class TicketMessageOut(ORMBase):
    id: int
    ticket_id: int
    sender_type: str
    message_type: str | None = None
    content: str
    attachment_count: int | None = 0
    created_by: int | None = None
    created_at: datetime | None = None


class TicketEventOut(ORMBase):
    id: int
    ticket_id: int
    event_type: str
    title: str
    description: str | None = None
    actor_type: str | None = None
    actor_user_id: int | None = None
    created_at: datetime | None = None
