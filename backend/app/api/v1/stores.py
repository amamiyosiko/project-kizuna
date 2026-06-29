from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import AuditLog, Store, User
from app.schemas.store import StoreCreate, StoreOut, StoreUpdate
from app.services.app_config import decrypt_value, encrypt_value, is_real_value, mask_secret
from app.services.authz import require_permission

router = APIRouter(prefix="/stores", tags=["stores"])


def _audit(db: Session, actor: User, action: str, store: Store, request: Request | None = None, extra: str | None = None) -> None:
    detail = (
        f"{store.store_name} / seller_id={'已填写' if store.seller_id else '未填写'} / "
        f"refresh_token={'已配置' if store.amazon_refresh_token_encrypted else '未配置'} / "
        f"sync={bool(store.amazon_sync_enabled)}"
    )
    if extra:
        detail += f" / {extra}"
    db.add(AuditLog(
        actor_user_id=actor.id,
        action=action,
        resource_type="store",
        resource_id=store.store_code,
        detail=detail,
        ip_address=request.client.host if request and request.client else None,
    ))


def _store_out(store: Store) -> StoreOut:
    raw_token = decrypt_value(store.amazon_refresh_token_encrypted) if getattr(store, "amazon_refresh_token_encrypted", None) else ""
    return StoreOut(
        id=store.id,
        store_name=store.store_name,
        store_code=store.store_code,
        platform=store.platform,
        marketplace=store.marketplace,
        marketplace_id=store.marketplace_id,
        seller_id=store.seller_id,
        amazon_sync_enabled=bool(store.amazon_sync_enabled),
        amazon_refresh_token_configured=is_real_value(raw_token),
        amazon_refresh_token_masked=mask_secret(raw_token) if is_real_value(raw_token) else None,
        amazon_last_sync_at=getattr(store, "amazon_last_sync_at", None),
        status=store.status,
        note=store.note,
        created_at=store.created_at,
    )


def _apply_store_payload(store: Store, payload: StoreCreate | StoreUpdate) -> None:
    data = payload.model_dump(exclude_unset=True)
    refresh_token = data.pop("amazon_refresh_token", None)
    clear_token = bool(data.pop("clear_amazon_refresh_token", False))
    for key, value in data.items():
        setattr(store, key, value)
    if clear_token:
        store.amazon_refresh_token_encrypted = None
    elif refresh_token is not None and refresh_token.strip():
        store.amazon_refresh_token_encrypted = encrypt_value(refresh_token.strip())


@router.get("", response_model=list[StoreOut])
def list_stores(_: User = Depends(require_permission("workitem.view")), db: Session = Depends(get_db)):
    stores = db.query(Store).order_by(Store.id.desc()).all()
    return [_store_out(store) for store in stores]


@router.post("", response_model=StoreOut)
def create_store(payload: StoreCreate, request: Request, current_user: User = Depends(require_permission("store.manage")), db: Session = Depends(get_db)):
    exists = db.query(Store).filter(Store.store_code == payload.store_code).first()
    if exists:
        raise HTTPException(status_code=400, detail="store_code already exists")
    data = payload.model_dump(exclude={"amazon_refresh_token"})
    store = Store(**data)
    if payload.amazon_refresh_token:
        store.amazon_refresh_token_encrypted = encrypt_value(payload.amazon_refresh_token.strip())
    db.add(store)
    db.flush()
    _audit(db, current_user, "store.create", store, request)
    db.commit()
    db.refresh(store)
    return _store_out(store)


@router.put("/{store_id}", response_model=StoreOut)
def update_store(store_id: int, payload: StoreUpdate, request: Request, current_user: User = Depends(require_permission("store.manage")), db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="store not found")
    _apply_store_payload(store, payload)
    _audit(db, current_user, "store.update", store, request)
    db.commit()
    db.refresh(store)
    return _store_out(store)


@router.delete("/{store_id}")
def delete_store(store_id: int, request: Request, current_user: User = Depends(require_permission("store.manage")), db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="store not found")
    _audit(db, current_user, "store.delete", store, request)
    db.delete(store)
    db.commit()
    return {"success": True}
