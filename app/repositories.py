from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func as sa_func
from sqlalchemy.orm import Session, selectinload

from app.models import Cliente, Producto, Venta, Pago, Usuario, VentaDetalle, VentaEliminada


def _escape_like(value: str) -> str:
    """Escapa caracteres especiales de LIKE para evitar manipulación de patrones."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class ClienteRepository:
    def __init__(self, db: Session):
        self.db = db

    def listar(self, q: str = "") -> list[Cliente]:
        stmt = select(Cliente)
        if q:
            q_esc = _escape_like(q)
            stmt = stmt.where(
                Cliente.nombre.ilike(f"%{q_esc}%", escape="\\")
                | Cliente.telefono.ilike(f"%{q_esc}%", escape="\\")
            )
        return self.db.execute(stmt.order_by(Cliente.nombre)).scalars().all()

    def obtener(self, cliente_id: int) -> Optional[Cliente]:
        return self.db.get(Cliente, cliente_id)

    def crear(self, nombre: str, telefono: str, direccion: Optional[str]) -> Cliente:
        cliente = Cliente(nombre=nombre, telefono=telefono, direccion=direccion)
        self.db.add(cliente)
        self.db.commit()
        self.db.refresh(cliente)
        return cliente

    def contar(self) -> int:
        return self.db.execute(select(sa_func.count(Cliente.id))).scalar()

    def actualizar(self, cliente_id: int, nombre: str, telefono: str, direccion: Optional[str]) -> Optional[Cliente]:
        cliente = self.obtener(cliente_id)
        if not cliente:
            return None
        cliente.nombre = nombre
        cliente.telefono = telefono
        cliente.direccion = direccion
        self.db.commit()
        self.db.refresh(cliente)
        return cliente

    def eliminar(self, cliente_id: int) -> bool:
        cliente = self.obtener(cliente_id)
        if not cliente:
            return False
        self.db.delete(cliente)
        self.db.commit()
        return True


class ProductoRepository:
    def __init__(self, db: Session):
        self.db = db

    def listar(self, q: str = "") -> list[Producto]:
        stmt = select(Producto)
        if q:
            q_esc = _escape_like(q)
            stmt = stmt.where(
                Producto.nombre.ilike(f"%{q_esc}%", escape="\\")
                | Producto.marca.ilike(f"%{q_esc}%", escape="\\")
                | Producto.referencia.ilike(f"%{q_esc}%", escape="\\")
            )
        return self.db.execute(stmt.order_by(Producto.nombre)).scalars().all()

    def obtener(self, producto_id: int) -> Optional[Producto]:
        return self.db.get(Producto, producto_id)

    def crear(self, nombre: str, marca: str, referencia: str, precio_compra: Decimal, precio: Decimal, stock: int = 0) -> Producto:
        producto = Producto(nombre=nombre, marca=marca, referencia=referencia, precio_compra=precio_compra, precio=precio, stock=stock)
        self.db.add(producto)
        self.db.commit()
        self.db.refresh(producto)
        return producto

    def contar(self) -> int:
        return self.db.execute(select(sa_func.count(Producto.id))).scalar()

    def actualizar(self, producto_id: int, nombre: str, marca: str, referencia: str,
                   precio_compra: Decimal, precio: Decimal) -> Optional[Producto]:
        producto = self.obtener(producto_id)
        if not producto:
            return None
        producto.nombre = nombre
        producto.marca = marca
        producto.referencia = referencia
        producto.precio_compra = precio_compra
        producto.precio = precio
        self.db.commit()
        self.db.refresh(producto)
        return producto

    def eliminar(self, producto_id: int) -> bool:
        producto = self.obtener(producto_id)
        if not producto:
            return False
        self.db.delete(producto)
        self.db.commit()
        return True


class VentaRepository:
    def __init__(self, db: Session):
        self.db = db

    def listar(self, q: str = "") -> list[Venta]:
        stmt = select(Venta).options(selectinload(Venta.pagos), selectinload(Venta.detalles))
        if q:
            q_esc = _escape_like(q)
            stmt = stmt.join(Venta.cliente).where(
                Cliente.nombre.ilike(f"%{q_esc}%", escape="\\")
                | Cliente.telefono.ilike(f"%{q_esc}%", escape="\\")
            )
        return self.db.execute(stmt.order_by(Venta.id.desc())).scalars().all()

    def obtener(self, venta_id: int) -> Optional[Venta]:
        return self.db.get(Venta, venta_id)

    def crear(self, cliente_id: int, fecha: date, total: Decimal,
              num_cuotas: int, frecuencia: str, notas: Optional[str],
              vendedor: str = "") -> Venta:
        venta = Venta(
            cliente_id=cliente_id, fecha=fecha, total=total,
            num_cuotas=num_cuotas, frecuencia=frecuencia, notas=notas,
            vendedor=vendedor,
        )
        self.db.add(venta)
        self.db.flush()
        self.db.refresh(venta)
        return venta


class PagoRepository:
    def __init__(self, db: Session):
        self.db = db

    def obtener(self, pago_id: int) -> Optional[Pago]:
        return self.db.get(Pago, pago_id)

    def crear(self, venta_id: int, numero_cuota: int, monto: Decimal,
              fecha_vencimiento: date) -> Pago:
        pago = Pago(
            venta_id=venta_id, numero_cuota=numero_cuota,
            monto=monto, fecha_vencimiento=fecha_vencimiento,
        )
        self.db.add(pago)
        return pago

    def pagar_por_venta_y_cuota(self, venta_id: int, numero_cuota: int, fecha_pago: date) -> Optional[Pago]:
        pago = self.db.execute(
            select(Pago).where(Pago.venta_id == venta_id, Pago.numero_cuota == numero_cuota)
        ).scalar_one_or_none()
        if pago and pago.fecha_pago is None:
            pago.fecha_pago = fecha_pago
        return pago

    def pagar(self, pago_id: int, fecha_pago: date) -> Optional[Pago]:
        pago = self.obtener(pago_id)
        if pago and pago.fecha_pago is None:
            pago.fecha_pago = fecha_pago
            self.db.commit()
            self.db.refresh(pago)
        return pago

    def reprogramar(self, pago_id: int, nueva_fecha: date) -> Optional[Pago]:
        pago = self.obtener(pago_id)
        if pago and pago.fecha_pago is None:
            pago.fecha_vencimiento = nueva_fecha
            self.db.commit()
            self.db.refresh(pago)
        return pago

    def listar_por_venta(self, venta_id: int) -> list[Pago]:
        return self.db.execute(
            select(Pago).where(Pago.venta_id == venta_id).order_by(Pago.numero_cuota)
        ).scalars().all()

    def cuotas_pendientes_por_cliente(self) -> list[tuple]:
        stmt = (
            select(Pago, Venta, Cliente)
            .join(Venta, Pago.venta_id == Venta.id)
            .join(Cliente, Venta.cliente_id == Cliente.id)
            .where(Pago.fecha_pago.is_(None))
            .order_by(Cliente.nombre, Venta.id, Pago.numero_cuota)
        )
        return self.db.execute(stmt).all()


class UsuarioRepository:
    def __init__(self, db: Session):
        self.db = db

    def listar(self) -> list[Usuario]:
        return self.db.execute(select(Usuario).order_by(Usuario.username)).scalars().all()

    def obtener(self, usuario_id: int) -> Optional[Usuario]:
        return self.db.get(Usuario, usuario_id)

    def obtener_por_username(self, username: str) -> Optional[Usuario]:
        return self.db.execute(
            select(Usuario).where(Usuario.username == username)
        ).scalar_one_or_none()

    def crear(self, username: str, password_hash: str, rol: str = "vendedor") -> Usuario:
        usuario = Usuario(username=username, password_hash=password_hash, rol=rol)
        self.db.add(usuario)
        self.db.commit()
        self.db.refresh(usuario)
        return usuario

    def actualizar_rol(self, usuario_id: int, rol: str) -> Optional[Usuario]:
        usuario = self.obtener(usuario_id)
        if not usuario:
            return None
        usuario.rol = rol
        self.db.commit()
        self.db.refresh(usuario)
        return usuario

    def cambiar_password(self, usuario_id: int, password_hash: str) -> Optional[Usuario]:
        usuario = self.obtener(usuario_id)
        if not usuario:
            return None
        usuario.password_hash = password_hash
        self.db.commit()
        self.db.refresh(usuario)
        return usuario

    def eliminar(self, usuario_id: int) -> bool:
        usuario = self.obtener(usuario_id)
        if not usuario:
            return False
        self.db.delete(usuario)
        self.db.commit()
        return True


class ReporteRepository:
    def __init__(self, db: Session):
        self.db = db

    def ganancia_total(self) -> Decimal:
        return self.db.execute(
            select(sa_func.coalesce(sa_func.sum(
                (VentaDetalle.precio_unitario - VentaDetalle.precio_compra) * VentaDetalle.cantidad
            ), 0))
        ).scalar()

    def total_recaudado(self, desde: date, hasta: date) -> Decimal:
        return self.db.execute(
            select(sa_func.coalesce(sa_func.sum(Pago.monto), 0))
            .where(Pago.fecha_pago.isnot(None))
            .where(Pago.fecha_pago >= desde)
            .where(Pago.fecha_pago <= hasta)
        ).scalar()

    def total_ventas_periodo(self, desde: date, hasta: date) -> Decimal:
        return self.db.execute(
            select(sa_func.coalesce(sa_func.sum(Venta.total), 0))
            .where(Venta.fecha >= desde)
            .where(Venta.fecha <= hasta)
        ).scalar()

    def ganancia_periodo(self, desde: date, hasta: date) -> Decimal:
        return self.db.execute(
            select(sa_func.coalesce(sa_func.sum(
                (VentaDetalle.precio_unitario - VentaDetalle.precio_compra) * VentaDetalle.cantidad
            ), 0))
            .join(VentaDetalle.venta)
            .where(Venta.fecha >= desde)
            .where(Venta.fecha <= hasta)
        ).scalar()

    def total_deuda_pendiente(self) -> Decimal:
        return self.db.execute(
            select(sa_func.coalesce(sa_func.sum(Pago.monto), 0))
            .where(Pago.fecha_pago.is_(None))
        ).scalar()

    def contar_ventas(self) -> int:
        return self.db.query(Venta).count()

    def contar_ventas_pendientes_entrega(self) -> int:
        from sqlalchemy import func
        return self.db.query(VentaDetalle.venta_id).filter(VentaDetalle.entregado == False).distinct().count()

    def ultimas_ventas(self, limit: int = 5) -> list[Venta]:
        return self.db.query(Venta).order_by(Venta.id.desc()).limit(limit).all()

    def listar_ventas_eliminadas(self) -> list[VentaEliminada]:
        from app.models import VentaEliminada
        return self.db.query(VentaEliminada).order_by(VentaEliminada.fecha_eliminacion.desc()).all()
