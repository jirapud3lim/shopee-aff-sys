"""Record live Meta submissions and prevent duplicate publication of a render."""

import sqlalchemy as sa

from alembic import op

revision = "c8f7b7774c28"
down_revision = "a7703ace91b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meta_publications",
        sa.Column("workspace_id", sa.String(36), primary_key=True),
        sa.Column("render_id", sa.String(36), primary_key=True),
        sa.Column("page_id", sa.String(30), nullable=False),
        sa.Column("caption", sa.Text(), nullable=False),
        sa.Column("comment_message", sa.Text(), nullable=True),
        sa.Column("ai_generated", sa.Boolean(), nullable=False),
        sa.Column("stage", sa.String(32), nullable=False),
        sa.Column("video_id", sa.String(30), nullable=True),
        sa.Column("comment_id", sa.String(80), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["workspace_id", "render_id"], ["renders.workspace_id", "renders.id"],
            ondelete="RESTRICT",
        ),
    )


def downgrade() -> None:
    op.drop_table("meta_publications")
