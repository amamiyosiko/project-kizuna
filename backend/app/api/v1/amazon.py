from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models import Store, Ticket, TicketEvent, TicketMessage, User
from app.schemas.amazon import (
    AmazonCredentialStatus,
    AmazonManualImportRequest,
    AmazonManualImportResponse,
    AmazonStatusOut,
    AmazonStoreStatus,
)
from app.schemas.ticket import TicketOut
from app.api.v1.tickets import VALID_PRIORITY, VALID_RISK, add_event, make_ticket_no

router = APIRouter(prefix="/amazon", tags=["amazon"])


def _has_real_value(value: str | None, placeholders: set[str]) -> bool:
    if not value:
        return False
    stripped = value.strip()
    return bool(stripped and stripped not in placeholders)


def _credential_status() -> AmazonCredentialStatus:
    return AmazonCredentialStatus(
        lwa_client_id=_has_real_value(settings.AMAZON_LWA_CLIENT_ID, {"your_lwa_client_id", "你的lwa_client_id"}),
        lwa_client_secret=_has_real_value(settings.AMAZON_LWA_CLIENT_SECRET, {"your_lwa_client_secret", "你的lwa_client_secret"}),
        refresh_token=_has_real_value(settings.AMAZON_REFRESH_TOKEN, {"your_refresh_token", "你的refresh_token"}),
        marketplace_id=_has_real_value(settings.AMAZON_MARKETPLACE_ID, {"A1VC38T7YXB528", "your_marketplace_id", "你的marketplace_id"}),
        endpoint_region=settings.AMAZON_REGION or "jp",
    )


@router.get("/status", response_model=AmazonStatusOut)
def amazon_status(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    stores = db.query(Store).filter(Store.platform == "Amazon").order_by(Store.id.asc()).all()
    store_statuses = [
        AmazonStoreStatus(
            id=s.id,
            store_name=s.store_name,
            store_code=s.store_code,
            marketplace=s.marketplace,
            seller_id=s.seller_id,
            status=s.status,
            seller_id_ready=bool((s.seller_id or "").strip()),
        )
        for s in stores
    ]
    credentials = _credential_status()
    missing: list[str] = []
    if not credentials.lwa_client_id:
        missing.append("AMAZON_LWA_CLIENT_ID")
    if not credentials.lwa_client_secret:
        missing.append("AMAZON_LWA_CLIENT_SECRET")
    if not credentials.refresh_token:
        missing.append("AMAZON_REFRESH_TOKEN")
    if not credentials.marketplace_id:
        missing.append("AMAZON_MARKETPLACE_ID")
    if not any(s.seller_id_ready for s in store_statuses):
        missing.append("至少一个 Amazon 店铺需要 Seller ID")

    ready = len(missing) == 0
    return AmazonStatusOut(
        credentials=credentials,
        stores=store_statuses,
        ready_for_next_stage=ready,
        auto_sync_enabled=False,
        missing_items=missing,
        next_step=(
            "凭证和 Seller ID 已具备。下一阶段可以开始接真实 SP-API 拉取买家消息。"
            if ready else
            "先补齐缺失项；本阶段仍可手动导入 Amazon 买家消息测试工作项流程。"
        ),
    )


@router.post("/manual-import", response_model=AmazonManualImportResponse)
def manual_import_amazon_message(
    payload: AmazonManualImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    store = db.query(Store).filter(Store.id == payload.store_id, Store.platform == "Amazon").first()
    if not store:
        raise HTTPException(status_code=404, detail="Amazon store not found")
    if not payload.buyer_name.strip():
        raise HTTPException(status_code=400, detail="buyer_name is required")
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="message is required")
    if payload.priority not in VALID_PRIORITY:
        raise HTTPException(status_code=400, detail="invalid priority")
    if payload.risk_level not in VALID_RISK:
        raise HTTPException(status_code=400, detail="invalid risk_level")

    now = datetime.utcnow()
    ticket = Ticket(
        ticket_no=make_ticket_no(db),
        platform="Amazon",
        marketplace=store.marketplace or "JP",
        store_id=store.id,
        buyer_name=payload.buyer_name.strip(),
        buyer_id=(payload.buyer_id or "").strip() or None,
        order_no=(payload.order_no or "").strip() or None,
        asin=(payload.asin or "").strip() or None,
        sku=(payload.sku or "").strip() or None,
        subject=(payload.subject or "Amazon 买家消息").strip(),
        status="NEW",
        priority=payload.priority,
        category=(payload.category or "其他").strip(),
        risk_level=payload.risk_level,
        language="ja",
        last_message_at=now,
    )
    db.add(ticket)
    db.flush()
    db.add(TicketMessage(
        ticket_id=ticket.id,
        sender_type="CUSTOMER",
        message_type="text",
        content=payload.message.strip(),
        created_by=None,
    ))
    add_event(db, ticket.id, "AMAZON_MANUAL_IMPORT", "Amazon 消息已手动导入", f"店铺：{store.store_code}", current_user)
    add_event(db, ticket.id, "MESSAGE_RECEIVED", "收到买家消息", payload.message[:300])
    db.commit()
    db.refresh(ticket)
    return AmazonManualImportResponse(ticket=TicketOut.model_validate(ticket))
