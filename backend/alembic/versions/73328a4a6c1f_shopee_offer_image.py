"""Add the observed product image to Shopee offers."""

import sqlalchemy as sa

from alembic import op

revision = "73328a4a6c1f"
down_revision = "4c0f239572eb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("shopee_offers", sa.Column("image_url", sa.String(2083), nullable=True))


def downgrade() -> None:
    op.drop_column("shopee_offers", "image_url")
