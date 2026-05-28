import json
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

logger = logging.getLogger(__name__)

from sqlalchemy.orm import Session

from app.repositories import (
    ClienteRepository,
    ProductoRepository,
    VentaRepository,
    PagoRepository,
)
from app.models import Producto, VentaDetalle, MovimientoStock, VentaEliminada


def generar_cuotas(total: Decimal, num_cuotas: int, fecha_inicio: date, frecuencia: str):
    if frecuencia not in ("quincenal", "mensual"):
        raise ValueError("Frecuencia no válida. Debe ser 'quincenal' o 'mensual'.")
    cuota_base = (total / Decimal(num_cuotas)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    delta_dias = 15 if frecuencia == "quincenal" else 30
    cuotas = []
    suma = Decimal("0")
    for i in range(num_cuotas):
        monto = cuota_base
        if i == num_cuotas - 1:
            monto = total - suma
        vencimiento = fecha_inicio + timedelta(days=delta_dias * (i + 1))
        cuotas.append({
            "numero": i + 1,
            "monto": monto,
            "fecha_vencimiento": vencimiento,
        })
        suma += monto
    return cuotas


def crear_venta(db: Session, cliente_id: int, fecha: date, total: Decimal,
                num_cuotas: int, frecuencia: str, notas: Optional[str],
                abono: Optional[Decimal] = None,
                productos: Optional[list[dict]] = None,
                vendedor: str = ""):
    venta_repo = VentaRepository(db)
    pago_repo = PagoRepository(db)
    abono = abono or Decimal("0")

    if abono >= total:
        num_cuotas = 0

    if productos:
        for item in productos:
            producto = db.get(Producto, item["producto_id"])
            if not producto:
                raise ValueError(f"Producto ID {item['producto_id']} no encontrado")

    venta = venta_repo.crear(cliente_id, fecha, total, num_cuotas, frecuencia, notas, vendedor=vendedor)

    if productos:
        for item in productos:
            producto = db.get(Producto, item["producto_id"])
            stock_anterior = producto.stock
            entregado = item.get("entregado", False)
            if entregado:
                if producto.stock < item["cantidad"]:
                    raise ValueError(f"Stock físico insuficiente para entregar {producto.nombre} inmediatamente.")
                producto.stock -= item["cantidad"]
            else:
                producto.stock_comprometido += item["cantidad"]

            detalle = VentaDetalle(
                venta_id=venta.id,
                producto_id=item["producto_id"],
                cantidad=item["cantidad"],
                precio_unitario=item["precio_unitario"],
                precio_compra=producto.precio_compra,
                entregado=entregado,
            )
            db.add(detalle)
            
            if entregado:
                db.add(MovimientoStock(
                    producto_id=producto.id,
                    cantidad=-item["cantidad"],
                    stock_anterior=stock_anterior,
                    stock_nuevo=producto.stock,
                    stock_comprometido_anterior=producto.stock_comprometido,
                    stock_comprometido_nuevo=producto.stock_comprometido,
                    tipo="venta",
                    motivo=f"Entrega INMEDIATA Venta #{venta.id}",
                    usuario=vendedor,
                    venta_id=venta.id,
                    fecha_hora=datetime.now(),
                ))
        db.flush()

    if abono > 0:
        pago = pago_repo.crear(venta.id, 0, abono, fecha)
        db.flush()
        pago_repo.pagar_por_venta_y_cuota(venta.id, 0, fecha, cobrado_por=vendedor)

    if num_cuotas > 0:
        restante = total - abono
        cuotas = generar_cuotas(restante, num_cuotas, fecha, frecuencia)
        for c in cuotas:
            pago_repo.crear(venta.id, c["numero"], c["monto"], c["fecha_vencimiento"])

    db.commit()
    db.refresh(venta)
    return venta


def cerrar_venta(db: Session, venta_id: int):
    venta_repo = VentaRepository(db)
    venta = venta_repo.obtener(venta_id)
    if not venta:
        return None
    pago_repo = PagoRepository(db)
    for pago in venta.pagos:
        if pago.fecha_pago is None:
            pago_repo.pagar(pago.id, date.today())
    db.commit()
    db.refresh(venta)
    return venta


def marcar_entregado(db: Session, detalle_id: int, usuario: str = ""):
    """Marca un detalle de venta como entregado al cliente."""
    detalle = db.get(VentaDetalle, detalle_id)
    if not detalle or detalle.entregado:
        return None
        
    producto = detalle.producto
    if producto.stock < detalle.cantidad:
        raise ValueError(f"Stock físico insuficiente ({producto.stock}) para cubrir entrega de {detalle.cantidad} uds.")

    producto.stock -= detalle.cantidad
    producto.stock_comprometido -= detalle.cantidad

    db.add(MovimientoStock(
        producto_id=producto.id,
        cantidad=-detalle.cantidad,
        stock_anterior=producto.stock + detalle.cantidad,
        stock_nuevo=producto.stock,
        stock_comprometido_anterior=producto.stock_comprometido + detalle.cantidad,
        stock_comprometido_nuevo=producto.stock_comprometido,
        tipo="venta",
        motivo=f"Entrega de Venta #{detalle.venta_id}",
        usuario=usuario,
        fecha_hora=datetime.now(),
    ))

    detalle.entregado = True
    db.commit()
    db.refresh(detalle)
    return detalle



def reprogramar_cuota(db: Session, pago_id: int, nueva_fecha: date):
    pago_repo = PagoRepository(db)
    return pago_repo.reprogramar(pago_id, nueva_fecha)


def obtener_deudores(db: Session):
    pago_repo = PagoRepository(db)
    resultados = pago_repo.cuotas_pendientes_por_cliente()

    deudores = {}
    for pago, venta, cliente in resultados:
        if cliente.id not in deudores:
            deudores[cliente.id] = {
                "cliente": cliente,
                "total_adeudado": Decimal("0.00"),
                "cuotas": [],
            }
        deudores[cliente.id]["total_adeudado"] += pago.monto
        deudores[cliente.id]["cuotas"].append({
            "venta_id": venta.id,
            "cuota_numero": pago.numero_cuota,
            "monto": pago.monto,
            "fecha_vencimiento": pago.fecha_vencimiento,
            "pago_id": pago.id,
        })

    return list(deudores.values())


def eliminar_venta(db: Session, venta_id: int, usuario: str = ""):
    """Elimina una venta, restaura el stock de los productos y registra los movimientos con auditoría."""
    venta_repo = VentaRepository(db)
    venta = venta_repo.obtener(venta_id)
    if not venta:
        return False

    # 1. Registrar Auditoría de Eliminación
    detalles_lista = []
    for d in venta.detalles:
        detalles_lista.append(f"{d.cantidad}x {d.producto.nombre} ({d.producto.marca})")
    
    total_pagado = sum(p.monto for p in venta.pagos if p.fecha_pago is not None)
    notas_motivo = "Eliminación con restauración de stock"
    if total_pagado > 0:
        notas_motivo += f". ALERTA: La venta tenía {total_pagado} cobrados que deben ser reembolsados/ajustados."
    
    audit = VentaEliminada(
        venta_id_original=venta.id,
        cliente_nombre=venta.cliente.nombre,
        vendedor_original=venta.vendedor,
        total=venta.total,
        fecha_venta=venta.fecha,
        fecha_eliminacion=datetime.now(),
        usuario_que_elimino=usuario,
        total_pagado_reembolsado=total_pagado,
        motivo=notas_motivo,
        detalles_json=json.dumps(detalles_lista)
    )
    db.add(audit)

    # 2. Restaurar stock de cada producto en la venta
    for detalle in venta.detalles:
        producto = detalle.producto
        stock_anterior = producto.stock

        if detalle.entregado:
            producto.stock += detalle.cantidad
            db.add(MovimientoStock(
                producto_id=producto.id,
                cantidad=detalle.cantidad,
                stock_anterior=stock_anterior,
                stock_nuevo=producto.stock,
                stock_comprometido_anterior=producto.stock_comprometido,
                stock_comprometido_nuevo=producto.stock_comprometido,
                tipo="ajuste",
                motivo=f"Eliminación Venta #{venta.id} (Devolución Física)",
                usuario=usuario,
                venta_id=None,
                fecha_hora=datetime.now(),
            ))
        else:
            producto.stock_comprometido -= detalle.cantidad

    # 3. Eliminar la venta físicamente (la cascada borrará detalles y pagos)
    db.delete(venta)
    db.commit()
    return True
