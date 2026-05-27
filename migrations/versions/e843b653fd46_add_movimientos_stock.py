"""add_movimientos_stock

Revision ID: e843b653fd46
Revises: 5ad3530f0fb0
Create Date: 2026-05-26 11:29:30.994751

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = 'e843b653fd46'
down_revision: Union[str, None] = '5ad3530f0fb0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    if 'movimientos_stock' not in inspector.get_table_names():
        op.create_table('movimientos_stock',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('producto_id', sa.Integer(), nullable=False),
            sa.Column('cantidad', sa.Integer(), nullable=False),
            sa.Column('stock_anterior', sa.Integer(), nullable=False),
            sa.Column('stock_nuevo', sa.Integer(), nullable=False),
            sa.Column('tipo', sa.String(length=20), nullable=False),
            sa.Column('motivo', sa.String(length=300), nullable=False),
            sa.Column('usuario', sa.String(length=100), nullable=False),
            sa.Column('venta_id', sa.Integer(), nullable=True),
            sa.Column('fecha_hora', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['producto_id'], ['productos.id'], ),
            sa.ForeignKeyConstraint(['venta_id'], ['ventas.id'], ),
            sa.PrimaryKeyConstraint('id')
        )


def downgrade() -> None:
    op.drop_table('movimientos_stock')
