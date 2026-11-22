"""Store affiliate links by product and channel."""

import sqlalchemy as sa

from alembic import op

revision = "a7703ace91b4"
down_revision = "3cb01a00d33f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_channel_links",
        sa.Column("workspace_id", sa.String(36), primary_key=True),
        sa.Column("product_id", sa.String(36), primary_key=True),
        sa.Column("channel", sa.String(48), primary_key=True),
        sa.Column("affiliate_url", sa.Text(), nullable=False),
        sa.Column("sub_id", sa.String(100), nullable=True),
        sa.ForeignKeyConstraint(
            ["workspace_id", "product_id"],
            ["products.workspace_id", "products.id"],
            ondelete="CASCADE",
        ),
    )


def downgrade() -> None:
    op.drop_table("product_channel_links")
