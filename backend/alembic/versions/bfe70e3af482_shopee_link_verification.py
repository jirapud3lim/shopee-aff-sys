"""Keep Shopee channel-link verification with the saved link."""

import sqlalchemy as sa
from alembic import op

revision = "bfe70e3af482"
down_revision = "73328a4a6c1f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("product_channel_links", sa.Column("shopee_verification", sa.String(16)))
    op.add_column("product_channel_links", sa.Column("shopee_verified_by", sa.String(36)))


def downgrade():
    op.drop_column("product_channel_links", "shopee_verified_by")
    op.drop_column("product_channel_links", "shopee_verification")
