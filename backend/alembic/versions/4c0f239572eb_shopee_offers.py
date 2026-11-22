"""Store workspace snapshots of Shopee Affiliate offers."""

import sqlalchemy as sa

from alembic import op

revision = "4c0f239572eb"
down_revision = "122df937c2eb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shopee_offers",
        sa.Column("workspace_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE")),
        sa.Column("offer_id", sa.String(20)),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("sold", sa.Integer(), nullable=False),
        sa.Column("sold_is_minimum", sa.Boolean(), nullable=False),
        sa.Column("price_satang", sa.BigInteger(), nullable=False),
        sa.Column("commission_bps", sa.Integer(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("workspace_id", "offer_id"),
    )


def downgrade() -> None:
    op.drop_table("shopee_offers")
