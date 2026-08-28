"""Add tenant table for multi tenant support

Revision ID: d640bf066f53
Revises: 5c8ac6e393f2
Create Date: 2026-08-28 14:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd640bf066f53'
down_revision = '5c8ac6e393f2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tenants table
    op.create_table('tenants',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('instance_name', sa.String(), nullable=False),
        sa.Column('instance_token', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tenants_instance_name'), 'tenants', ['instance_name'], unique=True)

    # Add tenant_id to contacts
    op.add_column('contacts', sa.Column('tenant_id', sa.String(), nullable=True))
    op.create_index(op.f('ix_contacts_tenant_id'), 'contacts', ['tenant_id'], unique=False)
    op.create_foreign_key('fk_contacts_tenant_id', 'contacts', 'tenants', ['tenant_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_contacts_tenant_id', 'contacts', type_='foreignkey')
    op.drop_index(op.f('ix_contacts_tenant_id'), table_name='contacts')
    op.drop_column('contacts', 'tenant_id')
    op.drop_index(op.f('ix_tenants_instance_name'), table_name='tenants')
    op.drop_table('tenants')
