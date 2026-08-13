"""add source_language to recipes

Recipes can now be translated on the way in (see
app/services/recipe_translator.py): `source_language` records the ISO 639-1
code they were originally extracted in, when that wasn't already Portuguese.
Null covers both "it was already Portuguese" and "couldn't tell" — nothing
downstream needs those two told apart. Existing rows all get null, the
correct value for content that predates translation.

Revision ID: ed0436ead057
Revises: b1e4c07a92d5
Create Date: 2026-08-13 05:25:11.710310

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'ed0436ead057'
down_revision: str | None = 'b1e4c07a92d5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('recipes', sa.Column('source_language', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('recipes', 'source_language')
