from datetime import datetime
from pydantic import BaseModel
from app.schemas.common import ORMBase


class StoreCreate(BaseModel):
    store_name: str
    store_code: str
    platform: str = "Amazon"
    marketplace: str = "JP"
    marketplace_id: str | None = "A1VC38T7YXB528"
    seller_id: str | None = None
    amazon_sync_enabled: bool = False
    amazon_refresh_token: str | None = None
    status: str = "active"
    note: str | None = None


class StoreUpdate(BaseModel):
    store_name: str | None = None
    store_code: str | None = None
    marketplace_id: str | None = None
    seller_id: str | None = None
    amazon_sync_enabled: bool | None = None
    amazon_refresh_token: str | None = None
    clear_amazon_refresh_token: bool | None = None
    status: str | None = None
    note: str | None = None


class StoreOut(ORMBase):
    id: int
    store_name: str
    store_code: str
    platform: str | None
    marketplace: str | None
    marketplace_id: str | None
    seller_id: str | None
    amazon_sync_enabled: bool | None
    amazon_refresh_token_configured: bool = False
    amazon_refresh_token_masked: str | None = None
    amazon_last_sync_at: datetime | None = None
    status: str | None
    note: str | None
    created_at: datetime | None
