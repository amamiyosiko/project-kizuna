from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models import Store, Ticket, TicketEvent, TicketMessage, User
from app.schemas.ticket import TicketCreate, TicketEventOut, TicketMessageCreate, TicketMessageOut, TicketOut, TicketUpdate

router = APIRouter(prefix="/tickets", tags=["tickets"])

VALID_STATUS = {"NEW", "OPEN", "PROCESSING", "WAITING_CUSTOMER", "WAITING_PLATFORM", "RESOLVED", "CLOSED"}
VALID_PRIORITY = {"P1", "P2", "P3", "P4"}


def make_ticket_no(db: Session) -> str:
    today = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"KZ-{today}-"
    count = db.query(func.count(Ticket.id)).filter(Ticket.ticket_no.like(f"{prefix}%")).scalar() or 0
    return f"{prefix}{count + 1:06d}"


def add_event(db: Session, ticket_id: int, event_type: str, title: str, description: str | None = None, actor: User | None = None):
    db.add(TicketEvent(
        ticket_id=ticket_id,
        event_type=event_type,
        title=title,
        description=description,
        actor_type="USER" if actor else "SYSTEM",
        actor_user_id=actor.id if actor else None,
    ))


@router.get("", response_model=list[TicketOut])
def list_tickets(
    store_id: int | None = None,
    status: str | None = None,
    priority: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Ticket)
    if store_id:
        query = query.filter(Ticket.store_id == store_id)
    if status:
        query = query.filter(Ticket.status == status)
    if priority:
        query = query.filter(Ticket.priority == priority)
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
    now = datetime.utcnow()
    ticket = Ticket(
        ticket_no=make_ticket_no(db),
        platform=store.platform or "Amazon",
        marketplace=store.marketplace or "JP",
        store_id=store.id,
        buyer_name=payload.buyer_name.strip(),
        buyer_id=payload.buyer_id,
        order_no=payload.order_no,
        asin=payload.asin,
        sku=payload.sku,
        subject=payload.subject or "Amazon Buyer Message",
        status="NEW",
        priority=payload.priority if payload.priority in VALID_PRIORITY else "P3",
        category=payload.category,
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
    add_event(db, ticket.id, "TICKET_CREATED", "Ticket created", f"Created manually by {current_user.username}", current_user)
    add_event(db, ticket.id, "MESSAGE_RECEIVED", "Customer message received", payload.initial_message[:300])
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
    old_status = ticket.status
    for k, v in data.items():
        if k == "status" and v is not None and v not in VALID_STATUS:
            raise HTTPException(status_code=400, detail="invalid status")
        if k == "priority" and v is not None and v not in VALID_PRIORITY:
            raise HTTPException(status_code=400, detail="invalid priority")
        setattr(ticket, k, v)
    now = datetime.utcnow()
    ticket.updated_at = now
    if ticket.status == "RESOLVED" and old_status != "RESOLVED":
        ticket.resolved_at = now
    if ticket.status == "CLOSED" and old_status != "CLOSED":
        ticket.closed_at = now
    if "status" in data and data["status"] != old_status:
        add_event(db, ticket.id, "STATUS_CHANGED", "Status changed", f"{old_status} -> {data['status']}", current_user)
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
    now = datetime.utcnow()
    message = TicketMessage(
        ticket_id=ticket.id,
        sender_type=sender,
        message_type=payload.message_type,
        content=payload.content.strip(),
        created_by=current_user.id if sender in {"AGENT", "AI", "SYSTEM"} else None,
    )
    ticket.last_message_at = now
    if sender == "CUSTOMER" and ticket.status in {"RESOLVED", "CLOSED"}:
        ticket.status = "OPEN"
    db.add(message)
    add_event(db, ticket.id, "MESSAGE_ADDED", f"{sender} message added", payload.content[:300], current_user if sender != "CUSTOMER" else None)
    db.commit()
    db.refresh(message)
    return message


@router.get("/{ticket_id}/events", response_model=list[TicketEventOut])
def list_ticket_events(ticket_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not db.query(Ticket.id).filter(Ticket.id == ticket_id).first():
        raise HTTPException(status_code=404, detail="ticket not found")
    return db.query(TicketEvent).filter(TicketEvent.ticket_id == ticket_id).order_by(TicketEvent.id.asc()).all()
