"""add_precio_compra_to_detalle

Revision ID: 5ad3530f0fb0
Revises: 452cc17c0ab3
Create Date: 2026-05-26 11:17:56.925959

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models import VentaDetalle, Producto

revision: str = '5ad3530f0fb0'
down_revision: Union[str, None] = '452cc17c0ab3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('venta_detalles', sa.Column('precio_compra', sa.Numeric(precision=14, scale=0), nullable=True))
    bind = op.get_bind()
    session = sa.orm.Session(bind=bind)
    detalles = session.query(VentaDetalle).all()
    for d in detalles:
        producto = session.get(Producto, d.producto_id)
        if producto:
            d.precio_compra = producto.precio_compra
    session.commit()


def downgrade() -> None:
    op.drop_column('venta_detalles', 'precio_compra')
