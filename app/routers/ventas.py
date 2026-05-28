from datetime import date
from decimal import Decimal
from urllib.parse import quote
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories import ClienteRepository, ProductoRepository, VentaRepository, PagoRepository
from app.schemas import ReprogramarCuota
from app.models import Venta, VentaDetalle
from app.services import (
    crear_venta, reprogramar_cuota, cerrar_venta, marcar_entregado, eliminar_venta
)
from starlette.concurrency import run_in_threadpool
from app.templating import templates

router = APIRouter()


@router.get("/ventas")
def listar_ventas(request: Request, db: Session = Depends(get_db), q: str = ""):
    repo = VentaRepository(db)
    ventas = repo.listar(q)
    ventas_con_pagado = []
    for v in ventas:
        total_pagado = sum(
            (p.monto for p in v.pagos if p.fecha_pago is not None),
            Decimal("0")
        )
        productos_pendientes = sum(
            1 for d in v.detalles if not d.entregado
        )
        ventas_con_pagado.append({
            "id": v.id,
            "cliente": v.cliente,
            "fecha": v.fecha,
            "total": v.total,
            "vendedor": v.vendedor,
            "num_cuotas": v.num_cuotas,
            "frecuencia": v.frecuencia,
            "total_pagado": total_pagado,
            "esta_pagada": total_pagado >= v.total,
            "productos_pendientes": productos_pendientes,
        })
    cliente_repo = ClienteRepository(db)
    producto_repo = ProductoRepository(db)
    clientes = cliente_repo.listar()
    productos = producto_repo.listar()
    error_venta = request.query_params.get("error_venta")
    return templates.TemplateResponse(request, "ventas.html", {
        "ventas": ventas_con_pagado,
        "clientes": clientes,
        "productos": productos,
        "hoy": date.today(),
        "q": q,
        "error_venta": error_venta,
        "username": request.session.get("username"),
        "rol": request.session.get("rol"),
    })


@router.post("/ventas")
async def registrar_venta(request: Request, db: Session = Depends(get_db)):
    try:
        form = await request.form()
        cliente_id = int(form["cliente_id"])
        fecha = date.fromisoformat(form["fecha"])
        total = Decimal(form["total"])
        abono = Decimal(form.get("abono", "0"))
        num_cuotas = int(form.get("num_cuotas", "0"))
        frecuencia = form.get("frecuencia", "mensual")
        notas = form.get("notas")

        cliente = ClienteRepository(db).obtener(cliente_id)
        if not cliente:
            raise ValueError("El cliente seleccionado no es válido")

        if abono < 0:
            raise ValueError("El abono no puede ser negativo")
        if abono >= total or num_cuotas <= 0:
            num_cuotas = 0

        productos_raw = []
        for key in form:
            if key.startswith("producto_id_"):
                idx = key.split("_")[-1]
                pid = form.get(f"producto_id_{idx}")
                cant = form.get(f"cantidad_{idx}")
                pu = form.get(f"precio_unitario_{idx}")
                entregado = form.get(f"entregado_{idx}") == "on"
                if pid and cant and int(cant) > 0:
                    productos_raw.append({
                        "producto_id": int(pid),
                        "cantidad": int(cant),
                        "precio_unitario": Decimal(pu),
                        "entregado": entregado,
                    })

        if not productos_raw:
            raise ValueError("Al menos un producto debe ser asignado a la venta")

        vendedor = request.session.get("username", "")
        venta = await run_in_threadpool(crear_venta, db, cliente_id, fecha, total, num_cuotas, frecuencia, notas, abono, productos_raw, vendedor)
        return RedirectResponse(url=f"/ventas/{venta.id}", status_code=303)
    except ValueError as e:
        return RedirectResponse(
            url=f"/ventas?error_venta={quote(str(e))}",
            status_code=303,
        )
    except Exception:
        return RedirectResponse(
            url="/ventas?error_venta=Error+al+registrar+la+venta.+Verifica+los+datos+e+intenta+de+nuevo.",
            status_code=303,
        )


@router.get("/ventas/{venta_id}")
def detalle_venta(venta_id: int, request: Request, db: Session = Depends(get_db)):
    repo = VentaRepository(db)
    venta = repo.obtener(venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    
    error = request.query_params.get("error")
    total_pagado = sum(
        (p.monto for p in venta.pagos if p.fecha_pago is not None),
        Decimal("0")
    )
    return templates.TemplateResponse(request, "detalle_venta.html", {
        "venta": venta,
        "total_pagado": total_pagado,
        "hoy": date.today(),
        "error": error,
        "username": request.session.get("username"),
        "rol": request.session.get("rol"),
    })


@router.post("/ventas/{venta_id}/cerrar")
def cerrar(venta_id: int, request: Request, db: Session = Depends(get_db)):
    venta = cerrar_venta(db, venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    return RedirectResponse(url=f"/ventas/{venta_id}", status_code=303)


@router.post("/pagar/{pago_id}")
def pagar(pago_id: int, db: Session = Depends(get_db)):
    pago = PagoRepository(db).pagar(pago_id, date.today())
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado o ya pagado")
    return RedirectResponse(url=f"/ventas/{pago.venta_id}", status_code=303)


@router.post("/reprogramar/{pago_id}")
def reprogramar(
    pago_id: int,
    request: Request,
    nueva_fecha: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        fecha = date.fromisoformat(nueva_fecha)
        ReprogramarCuota(nueva_fecha=fecha)
    except (ValueError, Exception) as e:
        pago_repo = PagoRepository(db)
        pago = pago_repo.obtener(pago_id)
        if not pago:
            raise HTTPException(status_code=404, detail="Pago no encontrado")
        venta = VentaRepository(db).obtener(pago.venta_id)
        total_pagado = sum(
            (p.monto for p in venta.pagos if p.fecha_pago is not None),
            Decimal("0")
        )
        return templates.TemplateResponse(request, "detalle_venta.html", {
            "venta": venta,
            "total_pagado": total_pagado,
            "error": str(e),
            "hoy": date.today(),
            "username": request.session.get("username"),
            "rol": request.session.get("rol"),
        })

    pago = reprogramar_cuota(db, pago_id, fecha)
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado o ya pagado")
    return RedirectResponse(url=f"/ventas/{pago.venta_id}", status_code=303)


@router.post("/ventas/detalle/{detalle_id}/entregar")
def entregar_producto(detalle_id: int, db: Session = Depends(get_db)):
    from app.models import VentaDetalle
    try:
        detalle = marcar_entregado(db, detalle_id)
        if not detalle:
            raise HTTPException(status_code=404, detail="Detalle no encontrado o ya entregado")
        return RedirectResponse(url=f"/ventas/{detalle.venta_id}", status_code=303)
    except ValueError as e:
        detalle = db.get(VentaDetalle, detalle_id)
        return RedirectResponse(url=f"/ventas/{detalle.venta_id}?error={quote(str(e))}", status_code=303)


@router.post("/ventas/{venta_id}/eliminar")
def eliminar(venta_id: int, request: Request, db: Session = Depends(get_db)):
    if request.session.get("rol") != "admin":
        raise HTTPException(status_code=403, detail="No tienes permisos para eliminar ventas")

    usuario = request.session.get("username", "admin")
    if eliminar_venta(db, venta_id, usuario):
        return RedirectResponse(url="/ventas", status_code=303)
    else:
        raise HTTPException(status_code=404, detail="Venta no encontrada")

