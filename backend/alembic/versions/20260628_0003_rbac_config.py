"""add rbac config center and audit logs

Revision ID: 20260628_0003
Revises: 20260628_0002
Create Date: 2026-06-28
"""

from __future__ import annotations

from alembic import op

revision = "20260628_0003"
down_revision = "20260628_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE roles ADD COLUMN IF NOT EXISTS status VARCHAR(30) DEFAULT 'active'")
    op.execute("ALTER TABLE roles ADD COLUMN IF NOT EXISTS is_system BOOLEAN DEFAULT FALSE")
    op.execute("ALTER TABLE roles ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT now()")
    op.execute("ALTER TABLE stores ADD COLUMN IF NOT EXISTS marketplace_id VARCHAR(80) DEFAULT 'A1VC38T7YXB528'")
    op.execute("ALTER TABLE stores ADD COLUMN IF NOT EXISTS amazon_sync_enabled BOOLEAN DEFAULT FALSE")

    op.execute("""
    CREATE TABLE IF NOT EXISTS permissions (
        id SERIAL PRIMARY KEY,
        code VARCHAR(100) UNIQUE NOT NULL,
        name VARCHAR(120) NOT NULL,
        "group" VARCHAR(80) DEFAULT 'general',
        description TEXT,
        created_at TIMESTAMP DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_permissions_code ON permissions (code)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS role_permissions (
        id SERIAL PRIMARY KEY,
        role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
        permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
        created_at TIMESTAMP DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_role_permissions_role_id ON role_permissions (role_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_role_permissions_permission_id ON role_permissions (permission_id)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_role_permissions_role_permission ON role_permissions (role_id, permission_id)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS system_configs (
        id SERIAL PRIMARY KEY,
        key VARCHAR(120) UNIQUE NOT NULL,
        "group" VARCHAR(80) DEFAULT 'General',
        label VARCHAR(150),
        value_encrypted TEXT,
        is_secret BOOLEAN DEFAULT TRUE,
        updated_by INTEGER REFERENCES users(id),
        created_at TIMESTAMP DEFAULT now(),
        updated_at TIMESTAMP DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_system_configs_key ON system_configs (key)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id SERIAL PRIMARY KEY,
        actor_user_id INTEGER REFERENCES users(id),
        action VARCHAR(120) NOT NULL,
        resource_type VARCHAR(80),
        resource_id VARCHAR(120),
        detail TEXT,
        ip_address VARCHAR(80),
        created_at TIMESTAMP DEFAULT now()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_actor_user_id ON audit_logs (actor_user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs (action)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_resource_type ON audit_logs (resource_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs (created_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_logs")
    op.execute("DROP TABLE IF EXISTS system_configs")
    op.execute("DROP INDEX IF EXISTS uq_role_permissions_role_permission")
    op.execute("DROP TABLE IF EXISTS role_permissions")
    op.execute("DROP TABLE IF EXISTS permissions")
    op.execute("ALTER TABLE stores DROP COLUMN IF EXISTS amazon_sync_enabled")
    op.execute("ALTER TABLE stores DROP COLUMN IF EXISTS marketplace_id")
    op.execute("ALTER TABLE roles DROP COLUMN IF EXISTS updated_at")
    op.execute("ALTER TABLE roles DROP COLUMN IF EXISTS is_system")
    op.execute("ALTER TABLE roles DROP COLUMN IF EXISTS status")
