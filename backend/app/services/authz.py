from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import Permission, Role, RolePermission, User

PERMISSIONS: dict[str, tuple[str, str]] = {
    "user.manage": ("用户管理", "创建、停用账号，分配角色"),
    "role.manage": ("角色管理", "管理角色与权限"),
    "config.manage": ("配置管理", "查看和修改普通配置"),
    "config.secret.manage": ("密钥管理", "维护 OpenAI、Gemini、Amazon 等密钥"),
    "store.manage": ("店铺管理", "维护店铺和 Seller ID"),
    "amazon.config.manage": ("Amazon配置", "维护 Amazon 接入配置"),
    "amazon.sync": ("Amazon同步", "同步 Amazon 订单和消息动作"),
    "workitem.view": ("查看工作项", "查看工作项列表和详情"),
    "workitem.create": ("创建工作项", "手动创建或导入工作项"),
    "workitem.update": ("更新工作项", "修改状态、分类、风险和优先级"),
    "workitem.reply": ("回复工作项", "保存客服回复"),
    "attachment.upload": ("附件上传", "上传和查看工作项附件"),
    "ai.use": ("AI助手", "使用 AI 回复助手"),
    "audit.view": ("日志查看", "查看操作日志"),
}

ROLE_PRESETS: dict[str, dict[str, object]] = {
    "super_admin": {
        "name": "超级管理员",
        "description": "拥有全部系统权限，可维护密钥和角色。",
        "permissions": list(PERMISSIONS.keys()),
    },
    "admin": {
        "name": "管理员",
        "description": "管理业务配置、店铺、同步和日志，不默认管理最高密钥。",
        "permissions": [
            "store.manage", "amazon.sync", "workitem.view", "workitem.create", "workitem.update",
            "workitem.reply", "attachment.upload", "ai.use", "audit.view", "config.manage",
        ],
    },
    "manager": {
        "name": "主管",
        "description": "查看和分配客服工作，处理风险和审核。",
        "permissions": [
            "workitem.view", "workitem.create", "workitem.update", "workitem.reply",
            "attachment.upload", "ai.use", "audit.view", "amazon.sync",
        ],
    },
    "agent": {
        "name": "客服",
        "description": "处理日常工作项、附件和 AI 草稿。",
        "permissions": ["workitem.view", "workitem.reply", "attachment.upload", "ai.use"],
    },
}


def seed_permissions_and_roles(db: Session) -> None:
    permission_map: dict[str, Permission] = {}
    for code, (name, desc) in PERMISSIONS.items():
        perm = db.query(Permission).filter(Permission.code == code).first()
        if not perm:
            perm = Permission(code=code, name=name, description=desc, group=code.split(".")[0])
            db.add(perm)
            db.flush()
        else:
            perm.name = name
            perm.description = desc
            perm.group = code.split(".")[0]
        permission_map[code] = perm

    role_map: dict[str, Role] = {}
    for code, preset in ROLE_PRESETS.items():
        role = db.query(Role).filter(Role.code == code).first()
        if not role:
            role = Role(code=code, name=str(preset["name"]), description=str(preset["description"]))
            db.add(role)
            db.flush()
        else:
            role.name = str(preset["name"])
            role.description = str(preset["description"])
        role.is_system = True
        role.status = "active"
        role_map[code] = role

        existing_codes = {
            rp.permission.code
            for rp in db.query(RolePermission).filter(RolePermission.role_id == role.id).all()
            if rp.permission
        }
        for perm_code in preset["permissions"]:  # type: ignore[index]
            if perm_code not in existing_codes:
                db.add(RolePermission(role_id=role.id, permission_id=permission_map[str(perm_code)].id))

    # Backfill old built-in roles from early versions.
    old_admin = db.query(Role).filter(Role.code == "admin").first()
    super_admin = role_map["super_admin"]
    for user in db.query(User).all():
        if user.username == "admin":
            user.role_id = super_admin.id
            user.role = "super_admin"
        elif not user.role_id:
            role = role_map.get(getattr(user, "role", None) or "agent") or role_map["agent"]
            user.role_id = role.id
            user.role = role.code
    db.commit()


def get_user_role(db: Session, user: User) -> Role | None:
    if user.role_id:
        role = db.query(Role).filter(Role.id == user.role_id).first()
        if role:
            return role
    if getattr(user, "role", None):
        return db.query(Role).filter(Role.code == user.role).first()
    return None


def get_user_permissions(db: Session, user: User) -> set[str]:
    role = get_user_role(db, user)
    if not role:
        return set()
    if role.code == "super_admin":
        return set(PERMISSIONS.keys())
    rows = db.query(RolePermission).join(Permission, RolePermission.permission_id == Permission.id).filter(RolePermission.role_id == role.id).all()
    return {row.permission.code for row in rows if row.permission}


def has_permission(db: Session, user: User, permission_code: str) -> bool:
    return permission_code in get_user_permissions(db, user)


def require_permission(permission_code: str):
    def dependency(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
        if not has_permission(db, user, permission_code):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"missing permission: {permission_code}")
        return user
    return dependency
