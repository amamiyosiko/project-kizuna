from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import AuditLog, Store, User
from app.schemas.store import StoreCreate, StoreOut, StoreUpdate
from app.services.authz import require_permission

router = APIRouter(prefix="/stores", tags=["stores"])


def _audit(db: Session, actor: User, action: str, store: Store, request: Request | None = None) -> None:
    db.add(AuditLog(
        actor_user_id=actor.id,
        action=action,
        resource_type="store",
        resource_id=store.store_code,
        detail=f"{store.store_name} / seller_id={'已填写' if store.seller_id else '未填写'} / sync={bool(store.amazon_sync_enabled)}",
        ip_address=request.client.host if request and request.client else None,
    ))


@router.get("", response_model=list[StoreOut])
def list_stores(_: User = Depends(require_permission("workitem.view")), db: Session = Depends(get_db)):
    return db.query(Store).order_by(Store.id.desc()).all()


@router.post("", response_model=StoreOut)
def create_store(payload: StoreCreate, request: Request, current_user: User = Depends(require_permission("store.manage")), db: Session = Depends(get_db)):
    exists = db.query(Store).filter(Store.store_code == payload.store_code).first()
    if exists:
        raise HTTPException(status_code=400, detail="store_code already exists")
    store = Store(**payload.model_dump())
    db.add(store)
    db.flush()
    _audit(db, current_user, "store.create", store, request)
    db.commit()
    db.refresh(store)
    return store


@router.put("/{store_id}", response_model=StoreOut)
def update_store(store_id: int, payload: StoreUpdate, request: Request, current_user: User = Depends(require_permission("store.manage")), db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="store not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(store, key, value)
    _audit(db, current_user, "store.update", store, request)
    db.commit()
    db.refresh(store)
    return store


@router.delete("/{store_id}")
def delete_store(store_id: int, request: Request, current_user: User = Depends(require_permission("store.manage")), db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="store not found")
    _audit(db, current_user, "store.delete", store, request)
    db.delete(store)
    db.commit()
    return {"success": True}
