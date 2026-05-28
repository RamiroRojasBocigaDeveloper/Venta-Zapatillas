from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Numeric, Integer, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    telefono: Mapped[str] = mapped_column(String(50), nullable=False)
    direccion: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    ventas: Mapped[list["Venta"]] = relationship("Venta", back_populates="cliente")


class Producto(Base):
    __tablename__ = "productos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    marca: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    referencia: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    precio_compra: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    precio: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stock_comprometido: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    detalles_venta: Mapped[list["VentaDetalle"]] = relationship("VentaDetalle", back_populates="producto")


class Venta(Base):
    __tablename__ = "ventas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cliente_id: Mapped[int] = mapped_column(Integer, ForeignKey("clientes.id"), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    num_cuotas: Mapped[int] = mapped_column(Integer, nullable=False)
    frecuencia: Mapped[str] = mapped_column(String(20), nullable=False)
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    vendedor: Mapped[str] = mapped_column(String(100), nullable=False, default="")

    cliente: Mapped["Cliente"] = relationship("Cliente", back_populates="ventas")
    detalles: Mapped[list["VentaDetalle"]] = relationship(
        "VentaDetalle", back_populates="venta", cascade="all, delete-orphan"
    )
    pagos: Mapped[list["Pago"]] = relationship(
        "Pago", back_populates="venta", cascade="all, delete-orphan",
        order_by="Pago.numero_cuota"
    )


class VentaDetalle(Base):
    __tablename__ = "venta_detalles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    venta_id: Mapped[int] = mapped_column(Integer, ForeignKey("ventas.id"), nullable=False)
    producto_id: Mapped[int] = mapped_column(Integer, ForeignKey("productos.id"), nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    precio_compra: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True, default=0)
    entregado: Mapped[bool] = mapped_column(default=False)

    venta: Mapped["Venta"] = relationship("Venta", back_populates="detalles")
    producto: Mapped["Producto"] = relationship("Producto", back_populates="detalles_venta")


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    rol: Mapped[str] = mapped_column(String(20), nullable=False, default="vendedor")


class MovimientoStock(Base):
    __tablename__ = "movimientos_stock"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    producto_id: Mapped[int] = mapped_column(Integer, ForeignKey("productos.id"), nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_anterior: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_nuevo: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_comprometido_anterior: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stock_comprometido_nuevo: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    motivo: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    usuario: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    venta_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("ventas.id"), nullable=True)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    producto: Mapped["Producto"] = relationship("Producto")
    venta: Mapped[Optional["Venta"]] = relationship("Venta")


class Pago(Base):
    __tablename__ = "pagos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    venta_id: Mapped[int] = mapped_column(Integer, ForeignKey("ventas.id"), nullable=False)
    numero_cuota: Mapped[int] = mapped_column(Integer, nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    fecha_vencimiento: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_pago: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    cobrado_por: Mapped[str] = mapped_column(String(100), nullable=False, default="")

    venta: Mapped["Venta"] = relationship("Venta", back_populates="pagos")


class VentaEliminada(Base):
    __tablename__ = "ventas_eliminadas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    venta_id_original: Mapped[int] = mapped_column(Integer, nullable=False)
    cliente_nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    vendedor_original: Mapped[str] = mapped_column(String(100), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    fecha_venta: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_eliminacion: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    usuario_que_elimino: Mapped[str] = mapped_column(String(100), nullable=False)
    total_pagado_reembolsado: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    motivo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detalles_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Lista de productos borrados
