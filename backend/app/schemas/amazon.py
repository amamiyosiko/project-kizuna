from pydantic import BaseModel

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


class AmazonStatusOut(BaseModel):
    stage: str = "v0.3.4"
    mode: str = "readiness"
    auto_sync_enabled: bool = False
    ready_for_next_stage: bool = False
    credentials: AmazonCredentialStatus
    stores: list[AmazonStoreStatus] = []
    missing_items: list[str] = []
    next_step: str | None = None


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
