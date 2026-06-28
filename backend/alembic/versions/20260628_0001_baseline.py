"""baseline existing Project Kizuna schema

Revision ID: 20260628_0001
Revises:
Create Date: 2026-06-28
"""

from __future__ import annotations

from alembic import op

revision = "20260628_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Baseline migration.
    # Existing production databases are already created by earlier versions.
    # New deployments still keep app startup create_all safety until full migration cutover.
    pass


def downgrade() -> None:
    pass
