"""Fix contact unique constraint for multi-tenancy

Revision ID: c8c324853175
Revises: d640bf066f53
Create Date: 2026-08-29 03:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c8c324853175'
down_revision = 'd640bf066f53'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove a restrição unique global antiga (apenas no número de telefone)
    op.drop_index('ix_contacts_phone_number', table_name='contacts')
    op.create_index(op.f('ix_contacts_phone_number'), 'contacts', ['phone_number'], unique=False)
    
    # Adiciona a restrição unique composta (tenant_id, phone_number)
    op.create_unique_constraint('uq_tenant_phone', 'contacts', ['tenant_id', 'phone_number'])


def downgrade() -> None:
    op.drop_constraint('uq_tenant_phone', 'contacts', type_='unique')
    op.drop_index(op.f('ix_contacts_phone_number'), table_name='contacts')
    op.create_index('ix_contacts_phone_number', 'contacts', ['phone_number'], unique=True)
