"""Add theme_preference column to user table

Revision ID: theme_preference_migration
Revises: edaf80aba97e
Create Date: 2025-10-18 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'theme_preference_migration'
down_revision = 'edaf80aba97e'
branch_labels = None
depends_on = None


def upgrade():
    # Add theme_preference column to user table
    op.add_column('user', sa.Column('theme_preference', sa.String(10), nullable=True, default='light'))


def downgrade():
    # Remove theme_preference column from user table
    op.drop_column('user', 'theme_preference')
