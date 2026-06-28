from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models import Store, Ticket, TicketEvent, TicketMessage, User
from app.schemas.ticket import (
    TicketCreate,
    TicketEventOut,
    TicketMessageCreate,
    TicketMessageOut,
    TicketOut,
    TicketStatsOut,
    TicketUpdate,
)

router = APIRouter(prefix="/tickets", tags=["tickets"])

VALID_STATUS = {"NEW", "OPEN", "PROCESSING", "WAITING_CUSTOMER", "WAITING_PLATFORM", "RESOLVED", "CLOSED"}
VALID_PRIORITY = {"P1", "P2", "P3", "P4"}
VALID_RISK = {"low", "medium", "high"}

STATUS_EVENT_TITLE = {
    "NEW": "新建",
    "OPEN": "已打开",
    "PROCESSING": "处理中",
    "WAITING_CUSTOMER": "等待客户",
    "WAITING_PLATFORM": "等待平台",
    "RESOLVED": "已解决",
    "CLOSED": "已关闭",
}


def make_ticket_no(db: Session) -> str:
    today = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"KZ-{today}-"
    count = db.query(func.count(Ticket.id)).filter(Ticket.ticket_no.like(f"{prefix}%")).scalar() or 0
    return f"{prefix}{count + 1:06d}"


def add_event(
    db: Session,
    ticket_id: int,
    event_type: str,
    title: str,
    description: str | None = None,
    actor: User | None = None,
) -> None:
    db.add(TicketEvent(
        ticket_id=ticket_id,
        event_type=event_type,
        title=title,
        description=description,
        actor_type="USER" if actor else "SYSTEM",
        actor_user_id=actor.id if actor else None,
    ))


def _count_by_status(db: Session, status: str) -> int:
    return db.query(func.count(Ticket.id)).filter(Ticket.status == status).scalar() or 0


@router.get("/stats/summary", response_model=TicketStatsOut)
def ticket_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return TicketStatsOut(
        total=db.query(func.count(Ticket.id)).scalar() or 0,
        new=_count_by_status(db, "NEW"),
        open=_count_by_status(db, "OPEN"),
        processing=_count_by_status(db, "PROCESSING"),
        waiting_customer=_count_by_status(db, "WAITING_CUSTOMER"),
        waiting_platform=_count_by_status(db, "WAITING_PLATFORM"),
        resolved=_count_by_status(db, "RESOLVED"),
        closed=_count_by_status(db, "CLOSED"),
        p1=db.query(func.count(Ticket.id)).filter(Ticket.priority == "P1").scalar() or 0,
        p2=db.query(func.count(Ticket.id)).filter(Ticket.priority == "P2").scalar() or 0,
        high_risk=db.query(func.count(Ticket.id)).filter(Ticket.risk_level == "high").scalar() or 0,
        today_created=db.query(func.count(Ticket.id)).filter(Ticket.created_at >= today_start).scalar() or 0,
    )


@router.get("", response_model=list[TicketOut])
def list_tickets(
    store_id: int | None = None,
    status: str | None = None,
    priority: str | None = None,
    risk_level: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Ticket)
    if store_id:
        query = query.filter(Ticket.store_id == store_id)
    if status:
        if status not in VALID_STATUS:
            raise HTTPException(status_code=400, detail="invalid status")
        query = query.filter(Ticket.status == status)
    if priority:
        if priority not in VALID_PRIORITY:
            raise HTTPException(status_code=400, detail="invalid priority")
        query = query.filter(Ticket.priority == priority)
    if risk_level:
        if risk_level not in VALID_RISK:
            raise HTTPException(status_code=400, detail="invalid risk_level")
        query = query.filter(Ticket.risk_level == risk_level)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(
            Ticket.ticket_no.ilike(like),
            Ticket.buyer_name.ilike(like),
            Ticket.order_no.ilike(like),
            Ticket.subject.ilike(like),
            Ticket.asin.ilike(like),
            Ticket.sku.ilike(like),
        ))
    return query.order_by(Ticket.last_message_at.desc().nullslast(), Ticket.id.desc()).limit(300).all()


@router.post("", response_model=TicketOut)
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    store = db.query(Store).filter(Store.id == payload.store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="store not found")
    if not payload.initial_message.strip():
        raise HTTPException(status_code=400, detail="initial_message is required")
    if payload.priority not in VALID_PRIORITY:
        raise HTTPException(status_code=400, detail="invalid priority")
    if payload.risk_level not in VALID_RISK:
        raise HTTPException(status_code=400, detail="invalid risk_level")

    now = datetime.utcnow()
    ticket = Ticket(
        ticket_no=make_ticket_no(db),
        platform=store.platform or "Amazon",
        marketplace=store.marketplace or "JP",
        store_id=store.id,
        buyer_name=payload.buyer_name.strip(),
        buyer_id=payload.buyer_id,
        order_no=(payload.order_no or "").strip() or None,
        asin=(payload.asin or "").strip() or None,
        sku=(payload.sku or "").strip() or None,
        subject=(payload.subject or "Amazon 买家消息").strip(),
        status="NEW",
        priority=payload.priority,
        category=(payload.category or "").strip() or None,
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
        content=payload.initial_message.strip(),
        created_by=None,
    ))
    add_event(db, ticket.id, "TICKET_CREATED", "工作项已创建", f"由 {current_user.username} 手动创建", current_user)
    add_event(db, ticket.id, "MESSAGE_RECEIVED", "收到买家消息", payload.initial_message[:300])
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="ticket not found")
    return ticket


@router.patch("/{ticket_id}", response_model=TicketOut)
def update_ticket(ticket_id: int, payload: TicketUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="ticket not found")

    data = payload.model_dump(exclude_unset=True)
    old_values = {
        "status": ticket.status,
        "priority": ticket.priority,
        "category": ticket.category,
        "risk_level": ticket.risk_level,
        "assigned_user_id": ticket.assigned_user_id,
        "subject": ticket.subject,
    }

    for key, value in data.items():
        if key == "status" and value is not None and value not in VALID_STATUS:
            raise HTTPException(status_code=400, detail="invalid status")
        if key == "priority" and value is not None and value not in VALID_PRIORITY:
            raise HTTPException(status_code=400, detail="invalid priority")
        if key == "risk_level" and value is not None and value not in VALID_RISK:
            raise HTTPException(status_code=400, detail="invalid risk_level")
        setattr(ticket, key, value)

    now = datetime.utcnow()
    ticket.updated_at = now
    if ticket.status == "RESOLVED" and old_values["status"] != "RESOLVED":
        ticket.resolved_at = now
    if ticket.status == "CLOSED" and old_values["status"] != "CLOSED":
        ticket.closed_at = now

    if "status" in data and data["status"] != old_values["status"]:
        old_label = STATUS_EVENT_TITLE.get(old_values["status"] or "", old_values["status"] or "-")
        new_label = STATUS_EVENT_TITLE.get(data["status"] or "", data["status"] or "-")
        add_event(db, ticket.id, "STATUS_CHANGED", "状态已更新", f"{old_label} → {new_label}", current_user)
    if "priority" in data and data["priority"] != old_values["priority"]:
        add_event(db, ticket.id, "PRIORITY_CHANGED", "优先级已更新", f"{old_values['priority'] or '-'} → {data['priority'] or '-'}", current_user)
    if "category" in data and data["category"] != old_values["category"]:
        add_event(db, ticket.id, "CATEGORY_CHANGED", "分类已更新", f"{old_values['category'] or '-'} → {data['category'] or '-'}", current_user)
    if "risk_level" in data and data["risk_level"] != old_values["risk_level"]:
        add_event(db, ticket.id, "RISK_CHANGED", "风险等级已更新", f"{old_values['risk_level'] or '-'} → {data['risk_level'] or '-'}", current_user)

    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/{ticket_id}/messages", response_model=list[TicketMessageOut])
def list_ticket_messages(ticket_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not db.query(Ticket.id).filter(Ticket.id == ticket_id).first():
        raise HTTPException(status_code=404, detail="ticket not found")
    return db.query(TicketMessage).filter(TicketMessage.ticket_id == ticket_id).order_by(TicketMessage.id.asc()).all()


@router.post("/{ticket_id}/messages", response_model=TicketMessageOut)
def create_ticket_message(ticket_id: int, payload: TicketMessageCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="ticket not found")
    sender = payload.sender_type.upper()
    if sender not in {"CUSTOMER", "AGENT", "AI", "SYSTEM"}:
        raise HTTPException(status_code=400, detail="invalid sender_type")
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="content is required")

    now = datetime.utcnow()
    message = TicketMessage(
        ticket_id=ticket.id,
        sender_type=sender,
        message_type=payload.message_type,
        content=content,
        created_by=current_user.id if sender in {"AGENT", "AI", "SYSTEM"} else None,
    )
    ticket.last_message_at = now
    if sender == "CUSTOMER" and ticket.status in {"RESOLVED", "CLOSED"}:
        old_status = ticket.status
        ticket.status = "OPEN"
        add_event(db, ticket.id, "STATUS_CHANGED", "客户追加消息，状态已重新打开", f"{old_status} → OPEN")
    db.add(message)
    title = {"CUSTOMER": "买家消息已记录", "AGENT": "客服回复已保存", "AI": "AI 消息已保存", "SYSTEM": "系统消息已保存"}[sender]
    add_event(db, ticket.id, "MESSAGE_ADDED", title, content[:300], current_user if sender != "CUSTOMER" else None)
    db.commit()
    db.refresh(message)
    return message


@router.get("/{ticket_id}/events", response_model=list[TicketEventOut])
def list_ticket_events(ticket_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not db.query(Ticket.id).filter(Ticket.id == ticket_id).first():
        raise HTTPException(status_code=404, detail="ticket not found")
    return db.query(TicketEvent).filter(TicketEvent.ticket_id == ticket_id).order_by(TicketEvent.id.asc()).all()
