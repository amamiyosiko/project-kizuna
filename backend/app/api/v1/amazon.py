from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.v1.tickets import VALID_PRIORITY, VALID_RISK, add_event, make_ticket_no
from app.core.deps import get_db
from app.models import AmazonSyncRun, AuditLog, Customer, Order, Store, Ticket, TicketMessage, User
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
    AmazonSyncRunOut,
)
from app.schemas.ticket import TicketOut
from app.services.amazon_spapi import (
    AmazonSPAPIError,
    configuration_overview,
    extract_orders,
    get_messaging_actions_for_order,
    get_recent_orders,
    get_recent_orders_pages,
    has_real_value,
)
from app.services.app_config import decrypt_value, get_config_value
from app.services.authz import require_permission

router = APIRouter(prefix="/amazon", tags=["amazon"])


def _audit(db: Session, actor: User | None, action: str, resource_type: str | None = None, resource_id: str | int | None = None, detail: dict | str | None = None, request: Request | None = None) -> None:
    db.add(AuditLog(
        actor_user_id=actor.id if actor else None,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        detail=json.dumps(detail, ensure_ascii=False) if isinstance(detail, dict) else detail,
        ip_address=request.client.host if request and request.client else None,
    ))


def _store_refresh_token(store: Store) -> str:
    token = decrypt_value(getattr(store, "amazon_refresh_token_encrypted", None)) if getattr(store, "amazon_refresh_token_encrypted", None) else ""
    return token.strip()


def _any_store_refresh_token(db: Session) -> bool:
    for store in _amazon_stores(db):
        if has_real_value(_store_refresh_token(store)):
            return True
    return has_real_value(get_config_value(db, "AMAZON_REFRESH_TOKEN", ""))


def _credential_status(db: Session) -> AmazonCredentialStatus:
    overview = configuration_overview()
    client_id = get_config_value(db, "AMAZON_LWA_CLIENT_ID", "")
    client_secret = get_config_value(db, "AMAZON_LWA_CLIENT_SECRET", "")
    marketplace = get_config_value(db, "AMAZON_MARKETPLACE_ID", "A1VC38T7YXB528")
    return AmazonCredentialStatus(
        lwa_client_id=has_real_value(client_id),
        lwa_client_secret=has_real_value(client_secret),
        refresh_token=_any_store_refresh_token(db),
        marketplace_id=has_real_value(str(marketplace or "")),
        endpoint_region=str(overview.get("endpoint_region") or "jp"),
        endpoint=overview.get("endpoint"),
        signing_region=overview.get("signing_region"),
        aws_signing_ready=bool(overview.get("aws_signing_ready")),
    )


def _amazon_stores(db: Session) -> list[Store]:
    return db.query(Store).filter(Store.platform == "Amazon").order_by(Store.id.asc()).all()


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def _order_total(order: dict[str, Any]) -> tuple[Decimal | None, str | None]:
    total = order.get("OrderTotal") or {}
    if not isinstance(total, dict):
        return None, None
    currency = total.get("CurrencyCode") or None
    amount_raw = total.get("Amount")
    if amount_raw in (None, ""):
        return None, currency
    try:
        return Decimal(str(amount_raw)), currency
    except (InvalidOperation, ValueError):
        return None, currency


def _buyer_name_from_order(order: dict[str, Any]) -> str:
    buyer = order.get("BuyerInfo") or {}
    if isinstance(buyer, dict):
        return buyer.get("BuyerName") or buyer.get("BuyerEmail") or "Amazon Buyer"
    return "Amazon Buyer"


def _customer_for_order(db: Session, order: dict[str, Any]) -> Customer:
    buyer_info = order.get("BuyerInfo") or {}
    buyer_id = None
    buyer_name = "Amazon Buyer"
    buyer_email_masked = None
    if isinstance(buyer_info, dict):
        buyer_id = buyer_info.get("BuyerId") or buyer_info.get("BuyerTaxInfo", {}).get("BuyerLegalCompanyName")
        buyer_name = buyer_info.get("BuyerName") or buyer_info.get("BuyerEmail") or buyer_name
        buyer_email_masked = buyer_info.get("BuyerEmail")
    if buyer_id:
        customer = db.query(Customer).filter(Customer.amazon_buyer_id == buyer_id).first()
        if customer:
            if buyer_name and customer.buyer_name != buyer_name:
                customer.buyer_name = buyer_name
            if buyer_email_masked and customer.buyer_email_masked != buyer_email_masked:
                customer.buyer_email_masked = buyer_email_masked
            return customer
    customer = Customer(
        marketplace="JP",
        buyer_name=buyer_name,
        buyer_email_masked=buyer_email_masked,
        amazon_buyer_id=buyer_id,
        total_orders=0,
        total_messages=0,
        risk_level="low",
    )
    db.add(customer)
    db.flush()
    return customer


def _upsert_order(db: Session, store: Store, order: dict[str, Any]) -> tuple[Order | None, bool, bool, str | None]:
    amazon_order_id = (order.get("AmazonOrderId") or "").strip()
    if not amazon_order_id:
        return None, False, False, None
    existing = db.query(Order).filter(Order.amazon_order_id == amazon_order_id).first()
    customer = _customer_for_order(db, order)
    amount, currency = _order_total(order)
    purchase_date = _parse_dt(order.get("PurchaseDate"))
    new_status = order.get("OrderStatus") or None
    old_status = existing.order_status if existing else None
    created = existing is None
    changed = False
    row = existing or Order(store_id=store.id, order_no=amazon_order_id, amazon_order_id=amazon_order_id)
    fields = {
        "store_id": store.id,
        "customer_id": customer.id,
        "order_status": new_status,
        "fulfillment_type": order.get("FulfillmentChannel") or None,
        "purchase_date": purchase_date,
        "total_amount": amount,
        "currency": currency or "JPY",
    }
    for key, value in fields.items():
        if getattr(row, key) != value:
            setattr(row, key, value)
            changed = True
    if created:
        db.add(row)
        changed = True
    if customer:
        customer.total_orders = max(customer.total_orders or 0, 1)
    db.flush()
    status_change = None
    if old_status and new_status and old_status != new_status:
        status_change = f"{old_status} → {new_status}"
    return row, created, changed and not created, status_change


def _order_summary_message(order: dict[str, Any], status_change: str | None = None) -> str:
    amazon_order_id = order.get("AmazonOrderId") or "-"
    order_status = order.get("OrderStatus") or "-"
    purchase_date = order.get("PurchaseDate") or "-"
    fulfillment = order.get("FulfillmentChannel") or "-"
    sales_channel = order.get("SalesChannel") or "-"
    ship_service = order.get("ShipmentServiceLevelCategory") or "-"
    amount, currency = _order_total(order)
    lines = [
        "Amazon SP-API 已同步订单。",
        f"注文番号：{amazon_order_id}",
        f"注文ステータス：{order_status}",
        f"購入日時：{purchase_date}",
        f"Fulfillment：{fulfillment}",
        f"SalesChannel：{sales_channel}",
        f"配送サービス：{ship_service}",
    ]
    if amount is not None:
        lines.append(f"注文金額：{amount} {currency or 'JPY'}")
    if status_change:
        lines.append(f"ステータス変更：{status_change}")
    lines.append("\n备注：本工作项来自订单同步，不代表已读取买家站内信；客服回复仍需人工确认。")
    return "\n".join(lines)


def _upsert_ticket_for_order(db: Session, store: Store, order: dict[str, Any], current_user: User, status_change: str | None = None) -> tuple[Ticket | None, bool, bool]:
    amazon_order_id = (order.get("AmazonOrderId") or "").strip()
    if not amazon_order_id:
        return None, False, False
    ticket = db.query(Ticket).filter(
        Ticket.platform == "Amazon",
        Ticket.store_id == store.id,
        Ticket.order_no == amazon_order_id,
    ).first()
    now = datetime.utcnow()
    buyer_name = _buyer_name_from_order(order)
    if not ticket:
        ticket = Ticket(
            ticket_no=make_ticket_no(db),
            platform="Amazon",
            marketplace=store.marketplace or "JP",
            store_id=store.id,
            buyer_name=buyer_name,
            buyer_id=None,
            order_no=amazon_order_id,
            asin=None,
            sku=None,
            subject=f"Amazon 订单同步：{amazon_order_id}",
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
            content=_order_summary_message(order),
            created_by=current_user.id,
        ))
        add_event(db, ticket.id, "AMAZON_ORDER_IMPORTED", "Amazon 订单已同步", amazon_order_id, current_user)
        return ticket, True, False

    changed = False
    if buyer_name and ticket.buyer_name != buyer_name:
        ticket.buyer_name = buyer_name
        changed = True
    if status_change:
        db.add(TicketMessage(
            ticket_id=ticket.id,
            sender_type="SYSTEM",
            message_type="text",
            content=_order_summary_message(order, status_change=status_change),
            created_by=current_user.id,
        ))
        add_event(db, ticket.id, "AMAZON_ORDER_UPDATED", "Amazon 订单状态已更新", status_change, current_user)
        ticket.last_message_at = now
        changed = True
    if changed:
        ticket.updated_at = now
    return ticket, False, changed


@router.get("/status", response_model=AmazonStatusOut)
def amazon_status(db: Session = Depends(get_db), current_user: User = Depends(require_permission("amazon.sync"))):
    stores = _amazon_stores(db)
    store_statuses = [
        AmazonStoreStatus(
            id=s.id,
            store_name=s.store_name,
            store_code=s.store_code,
            marketplace=s.marketplace,
            marketplace_id=s.marketplace_id,
            seller_id=s.seller_id,
            amazon_sync_enabled=bool(s.amazon_sync_enabled),
            status=s.status,
            seller_id_ready=bool((s.seller_id or "").strip()),
            refresh_token_ready=has_real_value(_store_refresh_token(s)),
            last_sync_at=getattr(s, "amazon_last_sync_at", None),
        )
        for s in stores
    ]
    credentials = _credential_status(db)
    missing: list[str] = []
    if not credentials.lwa_client_id:
        missing.append("AMAZON_LWA_CLIENT_ID")
    if not credentials.lwa_client_secret:
        missing.append("AMAZON_LWA_CLIENT_SECRET")
    if not credentials.refresh_token:
        missing.append("至少一个 Amazon 店铺需要配置 Refresh Token")
    if not credentials.marketplace_id:
        missing.append("AMAZON_MARKETPLACE_ID")
    if not credentials.aws_signing_ready:
        missing.append("AWS 签名凭证 / EC2 Role")
    if not any(s.seller_id_ready and s.refresh_token_ready and s.amazon_sync_enabled for s in store_statuses):
        missing.append("至少一个 Amazon 店铺需要 Seller ID、Refresh Token，并开启 Amazon 同步")

    ready = len(missing) == 0
    return AmazonStatusOut(
        credentials=credentials,
        stores=store_statuses,
        ready_for_next_stage=ready,
        auto_sync_enabled=False,
        missing_items=missing,
        next_step=(
            "凭证已具备。可以按店铺同步最近订单，并查看同步任务记录。"
            if ready else
            "先补齐缺失项；在凭证齐全前仍可手动导入 Amazon 买家消息。"
        ),
    )


@router.get("/sync-runs", response_model=list[AmazonSyncRunOut])
def list_sync_runs(
    store_id: int | None = None,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("amazon.sync")),
):
    query = db.query(AmazonSyncRun)
    if store_id:
        query = query.filter(AmazonSyncRun.store_id == store_id)
    return query.order_by(AmazonSyncRun.id.desc()).limit(min(max(limit, 1), 100)).all()


@router.post("/test-connection", response_model=AmazonConnectionTestResponse)
def test_amazon_connection(
    payload: AmazonConnectionTestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("amazon.sync")),
):
    try:
        store = db.query(Store).filter(Store.id == payload.store_id, Store.platform == "Amazon").first() if payload.store_id else None
        refresh_token = _store_refresh_token(store) if store else None
        marketplace = store.marketplace_id if store else None
        data = get_recent_orders(days=payload.days, max_results=1, marketplace_id_override=marketplace, refresh_token=refresh_token)
        orders = extract_orders(data)
        overview = configuration_overview()
        return AmazonConnectionTestResponse(
            success=True,
            message="SP-API 连接成功。即使最近没有订单，只要接口返回成功，就说明 LWA 与 AWS 签名链路已打通。",
            endpoint=overview.get("endpoint"),
            marketplace_id=marketplace or overview.get("marketplace_id"),
            store_id=store.id if store else None,
            store_name=store.store_name if store else None,
            order_count=len(orders),
            sample_order_ids=[o.get("AmazonOrderId", "") for o in orders if o.get("AmazonOrderId")][:5],
        )
    except AmazonSPAPIError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/import-orders", response_model=AmazonImportOrdersResponse)
def import_recent_orders(
    payload: AmazonImportOrdersRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("amazon.sync")),
):
    store = db.query(Store).filter(Store.id == payload.store_id, Store.platform == "Amazon").first()
    if not store:
        raise HTTPException(status_code=404, detail="Amazon store not found")
    if not store.amazon_sync_enabled:
        raise HTTPException(status_code=400, detail="该店铺尚未开启 Amazon 同步")
    if not (store.seller_id or "").strip():
        raise HTTPException(status_code=400, detail="该店铺缺少 Seller ID")
    if not has_real_value(_store_refresh_token(store)):
        raise HTTPException(status_code=400, detail="该店铺缺少 Refresh Token，请到店铺管理填写")

    run = AmazonSyncRun(
        store_id=store.id,
        status="running",
        sync_type="orders",
        requested_days=payload.days,
        requested_max_results=payload.max_results,
        requested_page_limit=payload.page_limit,
        started_by=current_user.id,
    )
    db.add(run)
    db.flush()

    try:
        orders, pages = get_recent_orders_pages(days=payload.days, max_results=payload.max_results, page_limit=payload.page_limit, marketplace_id_override=store.marketplace_id, refresh_token=_store_refresh_token(store))
    except AmazonSPAPIError as exc:
        run.status = "failed"
        run.error_message = str(exc)[:1000]
        run.finished_at = datetime.utcnow()
        _audit(db, current_user, "amazon.sync.failed", "store", store.store_code, {"error": run.error_message}, request)
        db.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    tickets_touched: list[Ticket] = []
    skipped = 0
    order_created = 0
    order_updated = 0
    ticket_created = 0
    ticket_updated = 0

    for order in orders:
        amazon_order_id = (order.get("AmazonOrderId") or "").strip()
        if not amazon_order_id:
            skipped += 1
            continue
        order_row, created_order, updated_order, status_change = _upsert_order(db, store, order)
        if not order_row:
            skipped += 1
            continue
        if created_order:
            order_created += 1
        elif updated_order:
            order_updated += 1
        ticket, created_ticket, updated_ticket = _upsert_ticket_for_order(db, store, order, current_user, status_change=status_change)
        if ticket:
            tickets_touched.append(ticket)
        if created_ticket:
            ticket_created += 1
        elif updated_ticket:
            ticket_updated += 1
        else:
            skipped += 1

    run.status = "success"
    run.fetched_count = len(orders)
    run.order_created_count = order_created
    run.order_updated_count = order_updated
    run.ticket_created_count = ticket_created
    run.ticket_updated_count = ticket_updated
    run.skipped_count = skipped
    run.finished_at = datetime.utcnow()
    store.amazon_last_sync_at = run.finished_at
    _audit(db, current_user, "amazon.sync.success", "store", store.store_code, {
        "pages": pages,
        "fetched": len(orders),
        "order_created": order_created,
        "order_updated": order_updated,
        "ticket_created": ticket_created,
        "ticket_updated": ticket_updated,
        "skipped": skipped,
    }, request)
    db.commit()
    db.refresh(run)
    unique_tickets: list[Ticket] = []
    seen = set()
    for t in tickets_touched:
        if t.id not in seen:
            seen.add(t.id)
            db.refresh(t)
            unique_tickets.append(t)
    return AmazonImportOrdersResponse(
        fetched_count=len(orders),
        order_created_count=order_created,
        order_updated_count=order_updated,
        ticket_created_count=ticket_created,
        ticket_updated_count=ticket_updated,
        skipped_count=skipped,
        tickets=[TicketOut.model_validate(t) for t in unique_tickets[:50]],
        sync_run=AmazonSyncRunOut.model_validate(run),
    )


@router.post("/messaging-actions", response_model=AmazonMessagingActionsResponse)
def check_messaging_actions(
    payload: AmazonMessagingActionsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("amazon.sync")),
):
    amazon_order_id = payload.amazon_order_id.strip()
    if not amazon_order_id:
        raise HTTPException(status_code=400, detail="amazon_order_id is required")
    try:
        store = db.query(Store).filter(Store.id == payload.store_id, Store.platform == "Amazon").first() if payload.store_id else None
        data = get_messaging_actions_for_order(amazon_order_id, marketplace_id_override=store.marketplace_id if store else None, refresh_token=_store_refresh_token(store) if store else None)
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
    current_user: User = Depends(require_permission("workitem.create")),
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
