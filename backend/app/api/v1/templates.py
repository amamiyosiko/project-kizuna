from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import ReplyTemplate
from app.schemas.template import ReplyTemplateCreate, ReplyTemplateOut, ReplyTemplateUpdate

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=list[ReplyTemplateOut])
def list_templates(
    category: str | None = Query(default=None),
    active_only: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    query = db.query(ReplyTemplate)
    if category:
        query = query.filter(ReplyTemplate.category == category)
    if active_only:
        query = query.filter(ReplyTemplate.is_active == True)  # noqa: E712
    return query.order_by(ReplyTemplate.category.asc(), ReplyTemplate.id.desc()).all()


@router.post("", response_model=ReplyTemplateOut)
def create_template(payload: ReplyTemplateCreate, db: Session = Depends(get_db)):
    template = ReplyTemplate(**payload.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.put("/{template_id}", response_model=ReplyTemplateOut)
def update_template(template_id: int, payload: ReplyTemplateUpdate, db: Session = Depends(get_db)):
    template = db.query(ReplyTemplate).filter(ReplyTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="template not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(template, key, value)
    db.commit()
    db.refresh(template)
    return template


@router.delete("/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db)):
    template = db.query(ReplyTemplate).filter(ReplyTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="template not found")
    db.delete(template)
    db.commit()
    return {"success": True}
