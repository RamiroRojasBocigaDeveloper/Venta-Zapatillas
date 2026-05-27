"""add entregado to ventadetalle

Revision ID: 0648c653fd47
Revises: e843b653fd46
Create Date: 2026-05-27 11:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0648c653fd47'
down_revision = 'e843b653fd46'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use batch_alter_table for SQLite compatibility
    with op.batch_alter_table('venta_detalles', schema=None) as batch_op:
        batch_op.add_column(sa.Column('entregado', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    with op.batch_alter_table('venta_detalles', schema=None) as batch_op:
        batch_op.drop_column('entregado')
