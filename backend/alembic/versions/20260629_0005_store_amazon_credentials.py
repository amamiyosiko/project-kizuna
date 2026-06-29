"""add per-store amazon authorization fields

Revision ID: 20260629_0005
Revises: 20260629_0004
Create Date: 2026-06-29
"""

from __future__ import annotations

from alembic import op

revision = "20260629_0005"
down_revision = "20260629_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE stores ADD COLUMN IF NOT EXISTS amazon_refresh_token_encrypted TEXT")
    op.execute("ALTER TABLE stores ADD COLUMN IF NOT EXISTS amazon_last_sync_at TIMESTAMP")


def downgrade() -> None:
    op.execute("ALTER TABLE stores DROP COLUMN IF EXISTS amazon_last_sync_at")
    op.execute("ALTER TABLE stores DROP COLUMN IF EXISTS amazon_refresh_token_encrypted")
