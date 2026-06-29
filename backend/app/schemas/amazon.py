from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.ticket import TicketOut


class AmazonStoreStatus(BaseModel):
    id: int
    store_name: str
    store_code: str
    marketplace: str | None = None
    marketplace_id: str | None = None
    seller_id: str | None = None
    amazon_sync_enabled: bool | None = False
    status: str | None = None
    seller_id_ready: bool = False
    refresh_token_ready: bool = False
    last_sync_at: datetime | None = None


class AmazonCredentialStatus(BaseModel):
    lwa_client_id: bool = False
    lwa_client_secret: bool = False
    refresh_token: bool = False
    marketplace_id: bool = False
    endpoint_region: str = "jp"
    endpoint: str | None = None
    signing_region: str | None = None
    aws_signing_ready: bool = False


class AmazonStatusOut(BaseModel):
    stage: str = "v0.3.8"
    mode: str = "production_spapi_multi_store"
    auto_sync_enabled: bool = False
    ready_for_next_stage: bool = False
    credentials: AmazonCredentialStatus
    stores: list[AmazonStoreStatus] = []
    missing_items: list[str] = []
    next_step: str | None = None
    official_limit_note: str = "v0.3.8 将 Amazon 应用配置与店铺授权拆开管理；每家店铺可单独维护 Seller ID、Refresh Token 与同步开关。"


class AmazonManualImportRequest(BaseModel):
    store_id: int
    buyer_name: str
    buyer_id: str | None = None
    order_no: str | None = None
    asin: str | None = None
    sku: str | None = None
    subject: str | None = None
    category: str = "配送未到"
    priority: str = "P3"
    risk_level: str = "low"
    message: str


class AmazonManualImportResponse(BaseModel):
    success: bool = True
    ticket: TicketOut
    message: str = "Amazon 买家消息已导入为工作项"


class AmazonConnectionTestRequest(BaseModel):
    store_id: int | None = None
    days: int = Field(default=3, ge=1, le=30)


class AmazonConnectionTestResponse(BaseModel):
    success: bool
    message: str
    endpoint: str | None = None
    marketplace_id: str | None = None
    store_id: int | None = None
    store_name: str | None = None
    order_count: int = 0
    sample_order_ids: list[str] = []


class AmazonImportOrdersRequest(BaseModel):
    store_id: int
    days: int = Field(default=3, ge=1, le=30)
    max_results: int = Field(default=20, ge=1, le=100)
    page_limit: int = Field(default=1, ge=1, le=10)


class AmazonSyncRunOut(BaseModel):
    id: int
    store_id: int | None = None
    status: str
    sync_type: str | None = None
    requested_days: int | None = None
    requested_max_results: int | None = None
    requested_page_limit: int | None = None
    fetched_count: int | None = 0
    order_created_count: int | None = 0
    order_updated_count: int | None = 0
    ticket_created_count: int | None = 0
    ticket_updated_count: int | None = 0
    skipped_count: int | None = 0
    error_message: str | None = None
    started_by: int | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    model_config = {"from_attributes": True}


class AmazonImportOrdersResponse(BaseModel):
    success: bool = True
    fetched_count: int = 0
    order_created_count: int = 0
    order_updated_count: int = 0
    ticket_created_count: int = 0
    ticket_updated_count: int = 0
    skipped_count: int = 0
    tickets: list[TicketOut] = []
    sync_run: AmazonSyncRunOut | None = None
    message: str = "Amazon 订单同步完成"


class AmazonMessagingActionsRequest(BaseModel):
    amazon_order_id: str
    store_id: int | None = None


class AmazonMessagingActionsResponse(BaseModel):
    success: bool = True
    amazon_order_id: str
    available_actions_count: int = 0
    available_action_titles: list[str] = []
    raw_keys: list[str] = []
