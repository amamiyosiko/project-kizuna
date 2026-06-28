from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Store
from app.schemas.store import StoreCreate, StoreOut, StoreUpdate

router = APIRouter(prefix="/stores", tags=["stores"])


@router.get("", response_model=list[StoreOut])
def list_stores(db: Session = Depends(get_db)):
    return db.query(Store).order_by(Store.id.desc()).all()


@router.post("", response_model=StoreOut)
def create_store(payload: StoreCreate, db: Session = Depends(get_db)):
    exists = db.query(Store).filter(Store.store_code == payload.store_code).first()
    if exists:
        raise HTTPException(status_code=400, detail="store_code already exists")
    store = Store(**payload.model_dump())
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


@router.put("/{store_id}", response_model=StoreOut)
def update_store(store_id: int, payload: StoreUpdate, db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="store not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(store, key, value)
    db.commit()
    db.refresh(store)
    return store


@router.delete("/{store_id}")
def delete_store(store_id: int, db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="store not found")
    db.delete(store)
    db.commit()
    return {"success": True}
