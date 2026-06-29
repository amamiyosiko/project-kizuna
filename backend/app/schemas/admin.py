from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.common import ORMBase


class PermissionOut(ORMBase):
    id: int
    code: str
    name: str
    group: str | None = None
    description: str | None = None


class RoleOut(ORMBase):
    id: int
    name: str
    code: str
    description: str | None = None
    status: str | None = None
    is_system: bool | None = False
    permissions: list[str] = []


class RoleCreate(BaseModel):
    name: str
    code: str = Field(pattern=r"^[a-zA-Z0-9_\-]+$")
    description: str | None = None
    permission_codes: list[str] = []


class RoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    permission_codes: list[str] | None = None


class AdminUserOut(ORMBase):
    id: int
    username: str
    email: str | None = None
    full_name: str | None = None
    role: str | None = None
    role_id: int | None = None
    role_name: str | None = None
    status: str | None = None
    must_change_password: bool | None = None
    created_at: datetime | None = None


class AdminUserCreate(BaseModel):
    username: str
    password: str
    email: str | None = None
    full_name: str | None = None
    role_code: str = "agent"
    status: str = "active"
    must_change_password: bool = True


class AdminUserUpdate(BaseModel):
    email: str | None = None
    full_name: str | None = None
    role_code: str | None = None
    status: str | None = None
    password: str | None = None
    must_change_password: bool | None = None


class ConfigOut(BaseModel):
    key: str
    group: str
    label: str
    is_secret: bool
    configured: bool
    value: str
    source: str


class ConfigUpdate(BaseModel):
    key: str
    value: str


class AuditLogOut(ORMBase):
    id: int
    actor_user_id: int | None = None
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    detail: str | None = None
    ip_address: str | None = None
    created_at: datetime | None = None
