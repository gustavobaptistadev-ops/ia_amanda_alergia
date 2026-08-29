"""Add appointments table for reminders

Revision ID: 7e8b9a1c2d3e
Revises: c8c324853175
Create Date: 2026-08-29 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7e8b9a1c2d3e'
down_revision = 'c8c324853175'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('appointments',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('contact_id', sa.String(), nullable=False),
        sa.Column('patient_name', sa.String(), nullable=False),
        sa.Column('appointment_time', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('reminder_24h_sent', sa.Boolean(), nullable=True),
        sa.Column('reminder_2h_sent', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_appointments_contact_id'), 'appointments', ['contact_id'], unique=False)
    op.create_index(op.f('ix_appointments_appointment_time'), 'appointments', ['appointment_time'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_appointments_appointment_time'), table_name='appointments')
    op.drop_index(op.f('ix_appointments_contact_id'), table_name='appointments')
    op.drop_table('appointments')
