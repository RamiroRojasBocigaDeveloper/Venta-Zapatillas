from datetime import date
from fastapi import APIRouter, Request, Depends, HTTPException

from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories import ClienteRepository, ProductoRepository, ReporteRepository
from app.services import obtener_deudores
from app.templating import templates

router = APIRouter()


@router.get("/")
def inicio(request: Request, db: Session = Depends(get_db)):
    cliente_repo = ClienteRepository(db)
    producto_repo = ProductoRepository(db)
    reporte_repo = ReporteRepository(db)

    total_clientes = cliente_repo.contar()
    total_productos = producto_repo.contar()
    total_ventas = reporte_repo.contar_ventas()
    ganancia_total = reporte_repo.ganancia_total()
    ultimas_ventas = reporte_repo.ultimas_ventas()

    deudores = obtener_deudores(db) or []
    total_deudores = len(deudores)
    top_deudores = deudores[:5]

    pendientes_entrega = reporte_repo.contar_ventas_pendientes_entrega()

    return templates.TemplateResponse(request, "inicio.html", {
        "username": request.session.get("username"),
        "rol": request.session.get("rol"),
        "total_clientes": total_clientes,
        "total_productos": total_productos,
        "total_ventas": total_ventas,
        "total_deudores": total_deudores,
        "pendientes_entrega": pendientes_entrega,
        "ganancia_total": ganancia_total,
        "ultimas_ventas": ultimas_ventas,
        "top_deudores": top_deudores,
    })


@router.get("/reportes")
def reportes(request: Request, db: Session = Depends(get_db)):
    desde = request.query_params.get("desde")
    hasta = request.query_params.get("hasta")
    hoy = date.today()
    try:
        fecha_desde = date.fromisoformat(desde) if desde else date(hoy.year, hoy.month, 1)
        fecha_hasta = date.fromisoformat(hasta) if hasta else hoy
    except (ValueError, TypeError):
        fecha_desde = date(hoy.year, hoy.month, 1)
        fecha_hasta = hoy

    reporte_repo = ReporteRepository(db)
    total_recaudado = reporte_repo.total_recaudado(fecha_desde, fecha_hasta)
    total_ventas_periodo = reporte_repo.total_ventas_periodo(fecha_desde, fecha_hasta)
    total_deuda = reporte_repo.total_deuda_pendiente()
    ganancia_periodo = reporte_repo.ganancia_periodo(fecha_desde, fecha_hasta)

    return templates.TemplateResponse(request, "reportes.html", {
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "total_recaudado": total_recaudado,
        "total_ventas_periodo": total_ventas_periodo,
        "total_deuda": total_deuda,
        "ganancia_periodo": ganancia_periodo,
        "username": request.session.get("username"),
        "rol": request.session.get("rol"),
    })


@router.get("/reporte/deudores")
def reporte_deudores(request: Request, db: Session = Depends(get_db)):
    deudores = obtener_deudores(db) or []
    return templates.TemplateResponse(request, "reporte_deudores.html", {
        "deudores": deudores,
        "username": request.session.get("username"),
        "rol": request.session.get("rol"),
    })


@router.get("/reporte/eliminadas")
def reporte_eliminadas(request: Request, db: Session = Depends(get_db)):
    if request.session.get("rol") != "admin":
        raise HTTPException(status_code=403, detail="No tienes permisos para ver este reporte")
    
    reporte_repo = ReporteRepository(db)
    eliminadas = reporte_repo.listar_ventas_eliminadas()
    return templates.TemplateResponse(request, "reporte_eliminadas.html", {
        "eliminadas": eliminadas,
        "username": request.session.get("username"),
        "rol": request.session.get("rol"),
    })
