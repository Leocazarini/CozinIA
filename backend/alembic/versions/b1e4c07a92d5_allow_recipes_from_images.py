"""allow recipes from images

Recipes can now be extracted from uploaded images, which have no page to
point back to: `source_url` becomes nullable, and `source_type` records
which of the two sources a recipe came from. Existing rows are all links.

Revision ID: b1e4c07a92d5
Revises: 54fdc92874fb
Create Date: 2026-08-12 19:20:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b1e4c07a92d5'
down_revision: str | None = '54fdc92874fb'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # server_default backfills every existing row as a link, and is kept on
    # the column so the link flow never has to name it explicitly.
    op.add_column(
        'recipes',
        sa.Column('source_type', sa.Text(), nullable=False, server_default='link'),
    )
    op.alter_column('recipes', 'source_url', existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    # Image recipes have no source_url, so they cannot survive a downgrade
    # to a NOT NULL column — drop them before restoring the constraint.
    op.execute("DELETE FROM recipes WHERE source_url IS NULL")
    op.alter_column('recipes', 'source_url', existing_type=sa.Text(), nullable=False)
    op.drop_column('recipes', 'source_type')
