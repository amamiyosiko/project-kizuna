from pydantic import BaseModel, Field

from app.schemas.ticket import TicketOut


class AmazonStoreStatus(BaseModel):
    id: int
    store_name: str
    store_code: str
    marketplace: str | None = None
    seller_id: str | None = None
    status: str | None = None
    seller_id_ready: bool = False


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
    stage: str = "v0.3.4.1"
    mode: str = "production_spapi"
    auto_sync_enabled: bool = False
    ready_for_next_stage: bool = False
    credentials: AmazonCredentialStatus
    stores: list[AmazonStoreStatus] = []
    missing_items: list[str] = []
    next_step: str | None = None
    official_limit_note: str = "SP-API Messaging API 主要用于发送买家消息和查询订单可用消息动作；买家站内信收件箱不作为本阶段自动拉取对象。"


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
    days: int = Field(default=3, ge=1, le=30)


class AmazonConnectionTestResponse(BaseModel):
    success: bool
    message: str
    endpoint: str | None = None
    marketplace_id: str | None = None
    order_count: int = 0
    sample_order_ids: list[str] = []


class AmazonImportOrdersRequest(BaseModel):
    store_id: int
    days: int = Field(default=3, ge=1, le=30)
    max_results: int = Field(default=20, ge=1, le=100)


class AmazonImportOrdersResponse(BaseModel):
    success: bool = True
    fetched_count: int = 0
    created_count: int = 0
    skipped_count: int = 0
    tickets: list[TicketOut] = []
    message: str = "Amazon 订单已同步为工作项"


class AmazonMessagingActionsRequest(BaseModel):
    amazon_order_id: str


class AmazonMessagingActionsResponse(BaseModel):
    success: bool = True
    amazon_order_id: str
    available_actions_count: int = 0
    available_action_titles: list[str] = []
    raw_keys: list[str] = []
