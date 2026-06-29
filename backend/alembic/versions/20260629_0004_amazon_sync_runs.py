"""amazon sync runs

Revision ID: 20260629_0004
Revises: 20260628_0003
Create Date: 2026-06-29
"""
from alembic import op
import sqlalchemy as sa

revision = "20260629_0004"
down_revision = "20260628_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "amazon_sync_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=True),
        sa.Column("sync_type", sa.String(length=50), nullable=True),
        sa.Column("requested_days", sa.Integer(), nullable=True),
        sa.Column("requested_max_results", sa.Integer(), nullable=True),
        sa.Column("requested_page_limit", sa.Integer(), nullable=True),
        sa.Column("fetched_count", sa.Integer(), nullable=True),
        sa.Column("order_created_count", sa.Integer(), nullable=True),
        sa.Column("order_updated_count", sa.Integer(), nullable=True),
        sa.Column("ticket_created_count", sa.Integer(), nullable=True),
        sa.Column("ticket_updated_count", sa.Integer(), nullable=True),
        sa.Column("skipped_count", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_by", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["started_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_amazon_sync_runs_id"), "amazon_sync_runs", ["id"], unique=False)
    op.create_index(op.f("ix_amazon_sync_runs_status"), "amazon_sync_runs", ["status"], unique=False)
    op.create_index(op.f("ix_amazon_sync_runs_store_id"), "amazon_sync_runs", ["store_id"], unique=False)
    op.create_index(op.f("ix_amazon_sync_runs_started_at"), "amazon_sync_runs", ["started_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_amazon_sync_runs_started_at"), table_name="amazon_sync_runs")
    op.drop_index(op.f("ix_amazon_sync_runs_store_id"), table_name="amazon_sync_runs")
    op.drop_index(op.f("ix_amazon_sync_runs_status"), table_name="amazon_sync_runs")
    op.drop_index(op.f("ix_amazon_sync_runs_id"), table_name="amazon_sync_runs")
    op.drop_table("amazon_sync_runs")
