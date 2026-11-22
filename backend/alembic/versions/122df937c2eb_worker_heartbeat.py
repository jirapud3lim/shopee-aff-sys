"""Record the last successful campaign worker iteration."""

import sqlalchemy as sa

from alembic import op

revision = "122df937c2eb"
down_revision = "9ac6cb168f72"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("campaign_worker_state", sa.Column("heartbeat_at", sa.BigInteger()))


def downgrade() -> None:
    op.drop_column("campaign_worker_state", "heartbeat_at")
