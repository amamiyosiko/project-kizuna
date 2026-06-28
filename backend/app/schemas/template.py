from datetime import datetime
from pydantic import BaseModel
from app.schemas.common import ORMBase


class ReplyTemplateCreate(BaseModel):
    category: str | None = None
    title: str
    content_ja: str
    content_zh: str | None = None
    risk_level: str = "low"
    is_active: bool = True


class ReplyTemplateUpdate(BaseModel):
    category: str | None = None
    title: str | None = None
    content_ja: str | None = None
    content_zh: str | None = None
    risk_level: str | None = None
    is_active: bool | None = None


class ReplyTemplateOut(ORMBase):
    id: int
    category: str | None
    title: str
    content_ja: str
    content_zh: str | None
    risk_level: str | None
    is_active: bool | None
    created_at: datetime | None
    updated_at: datetime | None = None
