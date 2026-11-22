"""Store normalized Shopee Affiliate Portal click and order rows."""

import sqlalchemy as sa

from alembic import op

revision = "06e312aaf36e"
down_revision = "c8f7b7774c28"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "affiliate_report_rows",
        sa.Column("workspace_id", sa.String(36), primary_key=True),
        sa.Column("kind", sa.String(6), primary_key=True),
        sa.Column("row_key", sa.String(64), primary_key=True),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("sub_id", sa.String(600)),
        sa.Column("source_channel", sa.String(256)),
        sa.Column("order_key", sa.String(64)),
        sa.Column("allocation", sa.String(5)),
        sa.Column("estimated", sa.BigInteger()),
        sa.Column("confirmed", sa.BigInteger()),
        sa.Column("status", sa.String(10)),
        sa.Column("updated", sa.String(36)),
        sa.Column("imported_at", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["organizations.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_affiliate_report_workspace_kind_day", "affiliate_report_rows", ["workspace_id", "kind", "day"]
    )


def downgrade() -> None:
    op.drop_index("ix_affiliate_report_workspace_kind_day", table_name="affiliate_report_rows")
    op.drop_table("affiliate_report_rows")
