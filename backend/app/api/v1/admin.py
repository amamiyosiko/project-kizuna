from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import get_password_hash
from app.db.session import get_db
from app.models import AuditLog, Permission, Role, RolePermission, User
from app.schemas.admin import (
    AdminUserCreate,
    AdminUserOut,
    AdminUserUpdate,
    AuditLogOut,
    ConfigOut,
    ConfigUpdate,
    PermissionOut,
    RoleCreate,
    RoleOut,
    RoleUpdate,
)
from app.services.app_config import CONFIG_DEFINITIONS, config_overview_items, set_config_value
from app.services.authz import get_user_permissions, get_user_role, require_permission

router = APIRouter(prefix="/admin", tags=["admin"])


def _audit(db: Session, actor: User | None, action: str, resource_type: str | None = None, resource_id: str | int | None = None, detail: dict | str | None = None, request: Request | None = None) -> None:
    if isinstance(detail, dict):
        detail_text = json.dumps(detail, ensure_ascii=False)
    else:
        detail_text = detail
    db.add(AuditLog(
        actor_user_id=actor.id if actor else None,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        detail=detail_text,
        ip_address=request.client.host if request and request.client else None,
    ))


def _role_permissions(db: Session, role_id: int) -> list[str]:
    rows = db.query(RolePermission).join(Permission, RolePermission.permission_id == Permission.id).filter(RolePermission.role_id == role_id).all()
    return sorted([row.permission.code for row in rows if row.permission])


def _role_out(db: Session, role: Role) -> RoleOut:
    return RoleOut(
        id=role.id,
        name=role.name,
        code=role.code,
        description=role.description,
        status=role.status,
        is_system=bool(role.is_system),
        permissions=_role_permissions(db, role.id),
    )


def _user_out(db: Session, user: User) -> AdminUserOut:
    role = get_user_role(db, user)
    return AdminUserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=role.code if role else user.role,
        role_id=role.id if role else user.role_id,
        role_name=role.name if role else None,
        status=user.status,
        must_change_password=bool(user.must_change_password),
        created_at=user.created_at,
    )


def _replace_role_permissions(db: Session, role: Role, permission_codes: list[str]) -> None:
    valid = db.query(Permission).filter(Permission.code.in_(permission_codes)).all() if permission_codes else []
    valid_map = {p.code: p for p in valid}
    missing = [code for code in permission_codes if code not in valid_map]
    if missing:
        raise HTTPException(status_code=400, detail="unknown permissions: " + ", ".join(missing))
    db.query(RolePermission).filter(RolePermission.role_id == role.id).delete()
    for perm in valid_map.values():
        db.add(RolePermission(role_id=role.id, permission_id=perm.id))


@router.get("/me/permissions")
def my_permissions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    role = get_user_role(db, current_user)
    return {
        "role": role.code if role else current_user.role,
        "role_name": role.name if role else None,
        "permissions": sorted(get_user_permissions(db, current_user)),
    }


@router.get("/permissions", response_model=list[PermissionOut])
def list_permissions(_: User = Depends(require_permission("role.manage")), db: Session = Depends(get_db)):
    return db.query(Permission).order_by(Permission.group.asc(), Permission.code.asc()).all()


@router.get("/roles", response_model=list[RoleOut])
def list_roles(_: User = Depends(require_permission("role.manage")), db: Session = Depends(get_db)):
    return [_role_out(db, role) for role in db.query(Role).order_by(Role.id.asc()).all()]


@router.post("/roles", response_model=RoleOut)
def create_role(payload: RoleCreate, request: Request, current_user: User = Depends(require_permission("role.manage")), db: Session = Depends(get_db)):
    if db.query(Role).filter(Role.code == payload.code).first():
        raise HTTPException(status_code=400, detail="role code already exists")
    role = Role(name=payload.name, code=payload.code, description=payload.description, status="active", is_system=False)
    db.add(role)
    db.flush()
    _replace_role_permissions(db, role, payload.permission_codes)
    _audit(db, current_user, "role.create", "role", role.code, {"name": role.name, "permissions": payload.permission_codes}, request)
    db.commit()
    db.refresh(role)
    return _role_out(db, role)


@router.put("/roles/{role_id}", response_model=RoleOut)
def update_role(role_id: int, payload: RoleUpdate, request: Request, current_user: User = Depends(require_permission("role.manage")), db: Session = Depends(get_db)):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="role not found")
    if role.code == "super_admin" and payload.status == "disabled":
        raise HTTPException(status_code=400, detail="super_admin role cannot be disabled")
    if payload.name is not None:
        role.name = payload.name
    if payload.description is not None:
        role.description = payload.description
    if payload.status is not None:
        role.status = payload.status
    if payload.permission_codes is not None:
        if role.code == "super_admin":
            raise HTTPException(status_code=400, detail="super_admin permissions are fixed")
        _replace_role_permissions(db, role, payload.permission_codes)
    _audit(db, current_user, "role.update", "role", role.code, {"name": role.name, "status": role.status}, request)
    db.commit()
    db.refresh(role)
    return _role_out(db, role)


@router.get("/users", response_model=list[AdminUserOut])
def list_users(_: User = Depends(require_permission("user.manage")), db: Session = Depends(get_db)):
    return [_user_out(db, user) for user in db.query(User).order_by(User.id.asc()).all()]


@router.post("/users", response_model=AdminUserOut)
def create_user(payload: AdminUserCreate, request: Request, current_user: User = Depends(require_permission("user.manage")), db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="username already exists")
    role = db.query(Role).filter(Role.code == payload.role_code, Role.status == "active").first()
    if not role:
        raise HTTPException(status_code=400, detail="role not found or disabled")
    user = User(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        password_hash=get_password_hash(payload.password),
        role_id=role.id,
        role=role.code,
        status=payload.status,
        must_change_password=payload.must_change_password,
    )
    db.add(user)
    db.flush()
    _audit(db, current_user, "user.create", "user", user.username, {"role": role.code, "status": user.status}, request)
    db.commit()
    db.refresh(user)
    return _user_out(db, user)


@router.put("/users/{user_id}", response_model=AdminUserOut)
def update_user(user_id: int, payload: AdminUserUpdate, request: Request, current_user: User = Depends(require_permission("user.manage")), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    if payload.email is not None:
        user.email = payload.email
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.status is not None:
        if user.id == current_user.id and payload.status != "active":
            raise HTTPException(status_code=400, detail="cannot disable current user")
        user.status = payload.status
    if payload.must_change_password is not None:
        user.must_change_password = payload.must_change_password
    if payload.password:
        if len(payload.password) < 8:
            raise HTTPException(status_code=400, detail="password too short")
        user.password_hash = get_password_hash(payload.password)
        user.must_change_password = True
    if payload.role_code is not None:
        role = db.query(Role).filter(Role.code == payload.role_code, Role.status == "active").first()
        if not role:
            raise HTTPException(status_code=400, detail="role not found or disabled")
        user.role_id = role.id
        user.role = role.code
    _audit(db, current_user, "user.update", "user", user.username, {"status": user.status, "role": user.role}, request)
    db.commit()
    db.refresh(user)
    return _user_out(db, user)


@router.get("/configs", response_model=list[ConfigOut])
def list_configs(_: User = Depends(require_permission("config.manage")), db: Session = Depends(get_db)):
    return config_overview_items(db)


@router.put("/configs/{key}", response_model=ConfigOut)
def update_config(key: str, payload: ConfigUpdate, request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if key not in CONFIG_DEFINITIONS:
        raise HTTPException(status_code=404, detail="config key not supported")
    definition = CONFIG_DEFINITIONS[key]
    required_permission = "config.secret.manage" if bool(definition.get("secret")) else "config.manage"
    if required_permission not in get_user_permissions(db, current_user):
        raise HTTPException(status_code=403, detail=f"missing permission: {required_permission}")
    if payload.key != key:
        raise HTTPException(status_code=400, detail="key mismatch")
    config = set_config_value(db, key, payload.value, current_user.id)
    _audit(db, current_user, "config.update", "config", key, {"secret": bool(definition.get("secret"))}, request)
    db.commit()
    return [item for item in config_overview_items(db) if item["key"] == config.key][0]


@router.get("/audit-logs", response_model=list[AuditLogOut])
def list_audit_logs(_: User = Depends(require_permission("audit.view")), db: Session = Depends(get_db)):
    return db.query(AuditLog).order_by(AuditLog.id.desc()).limit(100).all()
