"""add ticket attachment fields

Revision ID: 20260628_0002
Revises: 20260628_0001
Create Date: 2026-06-28
"""

from __future__ import annotations

from alembic import op

revision = "20260628_0002"
down_revision = "20260628_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL-safe migration. IF NOT EXISTS keeps new deployments safe because
    # app startup may already create tables from the latest SQLAlchemy models.
    op.execute("ALTER TABLE attachments ADD COLUMN IF NOT EXISTS ticket_id INTEGER")
    op.execute("ALTER TABLE attachments ADD COLUMN IF NOT EXISTS ticket_message_id INTEGER")
    op.execute("CREATE INDEX IF NOT EXISTS ix_attachments_ticket_id ON attachments (ticket_id)")

    op.execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'attachments_ticket_id_fkey'
      ) THEN
        ALTER TABLE attachments
        ADD CONSTRAINT attachments_ticket_id_fkey
        FOREIGN KEY (ticket_id) REFERENCES tickets(id);
      END IF;
    END $$;
    """)
    op.execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'attachments_ticket_message_id_fkey'
      ) THEN
        ALTER TABLE attachments
        ADD CONSTRAINT attachments_ticket_message_id_fkey
        FOREIGN KEY (ticket_message_id) REFERENCES ticket_messages(id);
      END IF;
    END $$;
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_attachments_ticket_id")
    op.execute("ALTER TABLE attachments DROP CONSTRAINT IF EXISTS attachments_ticket_message_id_fkey")
    op.execute("ALTER TABLE attachments DROP CONSTRAINT IF EXISTS attachments_ticket_id_fkey")
    op.execute("ALTER TABLE attachments DROP COLUMN IF EXISTS ticket_message_id")
    op.execute("ALTER TABLE attachments DROP COLUMN IF EXISTS ticket_id")
