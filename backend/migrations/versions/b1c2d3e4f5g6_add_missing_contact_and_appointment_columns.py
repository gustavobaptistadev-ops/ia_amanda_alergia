"""add missing contact and appointment columns

Revision ID: b1c2d3e4f5g6
Revises: 97019ffc3ccf
Create Date: 2026-09-05 02:13:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b1c2d3e4f5g6'
down_revision: Union[str, Sequence[str], None] = '97019ffc3ccf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    ddl_statements = [
        "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS insurance_operator VARCHAR;",
        "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS insurance_card_number VARCHAR;",
        "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS insurance_plan_name VARCHAR;",
        "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS insurance_coverage VARCHAR;",
        "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS insurance_accommodation VARCHAR;",
        "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS prep_reminder_sent BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS follow_up_sent BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS reschedule_count INTEGER DEFAULT 0;",
        "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS google_event_id VARCHAR;",
        "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS cancellation_reason VARCHAR;",
        "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS nps_sent BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS nps_score INTEGER;"
    ]
    for stmt in ddl_statements:
        op.execute(stmt)


def downgrade() -> None:
    pass
