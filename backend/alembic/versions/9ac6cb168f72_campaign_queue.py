"""Add durable publishing campaigns and the worker lease."""

import sqlalchemy as sa

from alembic import op

revision = "9ac6cb168f72"
down_revision = "06e312aaf36e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "campaigns",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("mode", sa.String(12), nullable=False),
        sa.Column("page_id", sa.String(30)),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint("workspace_id", "id"),
    )
    op.create_table(
        "campaign_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36), nullable=False),
        sa.Column("campaign_id", sa.String(36), nullable=False),
        sa.Column("render_id", sa.String(36), nullable=False),
        sa.Column("caption", sa.Text(), nullable=False),
        sa.Column("include_comment", sa.Boolean(), nullable=False),
        sa.Column("ai_generated", sa.Boolean(), nullable=False),
        sa.Column("scheduled_at", sa.BigInteger(), nullable=False),
        sa.Column("next_run_at", sa.BigInteger(), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("checks", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.String(30)),
        sa.Column("reel_url", sa.Text()),
        sa.Column("comment_url", sa.Text()),
        sa.Column("error", sa.Text()),
        sa.ForeignKeyConstraint(["workspace_id", "campaign_id"], ["campaigns.workspace_id", "campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id", "render_id"], ["renders.workspace_id", "renders.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("campaign_id", "render_id"),
    )
    op.create_index("ix_campaign_due", "campaign_items", ["state", "next_run_at"])
    table = op.create_table(
        "campaign_worker_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lease_token", sa.String(36)),
        sa.Column("lease_until", sa.BigInteger(), nullable=False),
        sa.Column("next_live_dispatch_at", sa.BigInteger(), nullable=False),
    )
    op.bulk_insert(table, [{"id": 1, "lease_until": 0, "next_live_dispatch_at": 0}])


def downgrade() -> None:
    op.drop_table("campaign_worker_state")
    op.drop_index("ix_campaign_due", table_name="campaign_items")
    op.drop_table("campaign_items")
    op.drop_table("campaigns")
