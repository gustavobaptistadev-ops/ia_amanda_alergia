"""add index contact_id to messages

Revision ID: 5c8ac6e393f2
Revises: 337ecd186ef7
Create Date: 2026-08-28 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5c8ac6e393f2'
down_revision = '337ecd186ef7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(op.f('ix_messages_contact_id'), 'messages', ['contact_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_messages_contact_id'), table_name='messages')
