from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.tickets import VALID_PRIORITY, VALID_RISK, add_event, make_ticket_no
from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models import Store, Ticket, TicketMessage, User
from app.schemas.amazon import (
    AmazonConnectionTestRequest,
    AmazonConnectionTestResponse,
    AmazonCredentialStatus,
    AmazonImportOrdersRequest,
    AmazonImportOrdersResponse,
    AmazonManualImportRequest,
    AmazonManualImportResponse,
    AmazonMessagingActionsRequest,
    AmazonMessagingActionsResponse,
    AmazonStatusOut,
    AmazonStoreStatus,
)
from app.schemas.ticket import TicketOut
from app.services.amazon_spapi import (
    AmazonSPAPIError,
    configuration_overview,
    get_messaging_actions_for_order,
    get_recent_orders,
    has_real_value,
)

router = APIRouter(prefix="/amazon", tags=["amazon"])


def _credential_status() -> AmazonCredentialStatus:
    overview = configuration_overview()
    return AmazonCredentialStatus(
        lwa_client_id=has_real_value(settings.AMAZON_LWA_CLIENT_ID),
        lwa_client_secret=has_real_value(settings.AMAZON_LWA_CLIENT_SECRET),
        refresh_token=has_real_value(settings.AMAZON_REFRESH_TOKEN),
        marketplace_id=has_real_value(settings.AMAZON_MARKETPLACE_ID),
        endpoint_region=settings.AMAZON_REGION or "jp",
        endpoint=overview.get("endpoint"),
        signing_region=overview.get("signing_region"),
        aws_signing_ready=bool(overview.get("aws_signing_ready")),
    )


def _amazon_stores(db: Session) -> list[Store]:
    return db.query(Store).filter(Store.platform == "Amazon").order_by(Store.id.asc()).all()


def _orders_from_response(data: dict[str, Any]) -> list[dict[str, Any]]:
    payload = data.get("payload") if isinstance(data, dict) else {}
    if isinstance(payload, dict) and isinstance(payload.get("Orders"), list):
        return payload.get("Orders") or []
    if isinstance(data.get("Orders"), list):
        return data.get("Orders") or []
    return []


@router.get("/status", response_model=AmazonStatusOut)
def amazon_status(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    stores = _amazon_stores(db)
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
    if not credentials.aws_signing_ready:
        missing.append("AWS 签名凭证 / EC2 Role")
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
            "凭证已具备。可以点击【测试 SP-API 连接】，成功后导入最近订单生成工作项。"
            if ready else
            "先补齐缺失项；在凭证齐全前仍可手动导入 Amazon 买家消息。"
        ),
    )


@router.post("/test-connection", response_model=AmazonConnectionTestResponse)
def test_amazon_connection(
    payload: AmazonConnectionTestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        data = get_recent_orders(days=payload.days, max_results=1)
        orders = _orders_from_response(data)
        overview = configuration_overview()
        return AmazonConnectionTestResponse(
            success=True,
            message="SP-API 连接成功。即使最近没有订单，只要接口返回成功，就说明 LWA 与 AWS 签名链路已打通。",
            endpoint=overview.get("endpoint"),
            marketplace_id=overview.get("marketplace_id"),
            order_count=len(orders),
            sample_order_ids=[o.get("AmazonOrderId", "") for o in orders if o.get("AmazonOrderId")][:5],
        )
    except AmazonSPAPIError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/import-orders", response_model=AmazonImportOrdersResponse)
def import_recent_orders(
    payload: AmazonImportOrdersRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    store = db.query(Store).filter(Store.id == payload.store_id, Store.platform == "Amazon").first()
    if not store:
        raise HTTPException(status_code=404, detail="Amazon store not found")
    try:
        data = get_recent_orders(days=payload.days, max_results=payload.max_results)
    except AmazonSPAPIError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    orders = _orders_from_response(data)
    created: list[Ticket] = []
    skipped = 0
    now = datetime.utcnow()
    for order in orders:
        amazon_order_id = (order.get("AmazonOrderId") or "").strip()
        if not amazon_order_id:
            skipped += 1
            continue
        exists = db.query(Ticket).filter(
            Ticket.platform == "Amazon",
            Ticket.store_id == store.id,
            Ticket.order_no == amazon_order_id,
        ).first()
        if exists:
            skipped += 1
            continue

        subject = f"Amazon 订单同步：{amazon_order_id}"
        order_status = order.get("OrderStatus") or "-"
        purchase_date = order.get("PurchaseDate") or "-"
        fulfillment = order.get("FulfillmentChannel") or "-"
        sales_channel = order.get("SalesChannel") or "-"
        initial_message = (
            "Amazon SP-API 已同步订单。\n"
            f"注文番号：{amazon_order_id}\n"
            f"注文ステータス：{order_status}\n"
            f"購入日時：{purchase_date}\n"
            f"Fulfillment：{fulfillment}\n"
            f"SalesChannel：{sales_channel}\n\n"
            "备注：本工作项来自订单同步，不代表已读取买家站内信。若买家消息仍未开放自动拉取，请继续使用手动导入或 Amazon Seller Central 对照处理。"
        )
        ticket = Ticket(
            ticket_no=make_ticket_no(db),
            platform="Amazon",
            marketplace=store.marketplace or "JP",
            store_id=store.id,
            buyer_name="Amazon Buyer",
            buyer_id=None,
            order_no=amazon_order_id,
            asin=None,
            sku=None,
            subject=subject,
            status="NEW",
            priority="P3",
            category="Amazon订单同步",
            risk_level="low",
            language="ja",
            last_message_at=now,
        )
        db.add(ticket)
        db.flush()
        db.add(TicketMessage(
            ticket_id=ticket.id,
            sender_type="SYSTEM",
            message_type="text",
            content=initial_message,
            created_by=current_user.id,
        ))
        add_event(db, ticket.id, "AMAZON_ORDER_IMPORTED", "Amazon 订单已同步", amazon_order_id, current_user)
        created.append(ticket)
    db.commit()
    for t in created:
        db.refresh(t)
    return AmazonImportOrdersResponse(
        fetched_count=len(orders),
        created_count=len(created),
        skipped_count=skipped,
        tickets=[TicketOut.model_validate(t) for t in created],
    )


@router.post("/messaging-actions", response_model=AmazonMessagingActionsResponse)
def check_messaging_actions(
    payload: AmazonMessagingActionsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    amazon_order_id = payload.amazon_order_id.strip()
    if not amazon_order_id:
        raise HTTPException(status_code=400, detail="amazon_order_id is required")
    try:
        data = get_messaging_actions_for_order(amazon_order_id)
    except AmazonSPAPIError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    embedded = data.get("_embedded") if isinstance(data, dict) else {}
    actions = embedded.get("actions") if isinstance(embedded, dict) else []
    titles: list[str] = []
    if isinstance(actions, list):
        for action in actions:
            schema = action.get("schema") or action.get("_embedded", {}).get("schema") if isinstance(action, dict) else None
            title = schema.get("title") if isinstance(schema, dict) else None
            if title:
                titles.append(str(title))
    return AmazonMessagingActionsResponse(
        amazon_order_id=amazon_order_id,
        available_actions_count=len(actions) if isinstance(actions, list) else 0,
        available_action_titles=titles[:20],
        raw_keys=list(data.keys())[:20] if isinstance(data, dict) else [],
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
