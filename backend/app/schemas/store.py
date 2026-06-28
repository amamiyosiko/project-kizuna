from datetime import datetime
from pydantic import BaseModel
from app.schemas.common import ORMBase


class StoreCreate(BaseModel):
    store_name: str
    store_code: str
    platform: str = "Amazon"
    marketplace: str = "JP"
    seller_id: str | None = None
    status: str = "active"
    note: str | None = None


class StoreUpdate(BaseModel):
    store_name: str | None = None
    store_code: str | None = None
    seller_id: str | None = None
    status: str | None = None
    note: str | None = None


class StoreOut(ORMBase):
    id: int
    store_name: str
    store_code: str
    platform: str | None
    marketplace: str | None
    seller_id: str | None
    status: str | None
    note: str | None
    created_at: datetime | None
