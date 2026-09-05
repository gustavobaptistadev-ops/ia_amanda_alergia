"""add anamnesis fields to appointments

Revision ID: anamnesis_fields_1
Revises: 
Create Date: 2026-09-05 07:50:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'anamnesis_fields_1'
down_revision = '4912ad9b7b2a'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('appointments', sa.Column('symptom', sa.String(), nullable=True))
    op.add_column('appointments', sa.Column('symptom_duration', sa.String(), nullable=True))
    op.add_column('appointments', sa.Column('current_medication', sa.String(), nullable=True))

def downgrade() -> None:
    op.drop_column('appointments', 'current_medication')
    op.drop_column('appointments', 'symptom_duration')
    op.drop_column('appointments', 'symptom')
