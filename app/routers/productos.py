from datetime import datetime
from urllib.parse import quote
from decimal import Decimal
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from sqlalchemy import select
from app.repositories import ProductoRepository, UsuarioRepository
from app.models import Producto, MovimientoStock
from app.templating import templates

router = APIRouter()


@router.get("/productos")
def listar_productos(request: Request, db: Session = Depends(get_db), q: str = ""):
    repo = ProductoRepository(db)
    productos = repo.listar(q)
    movimientos = db.execute(select(MovimientoStock).order_by(MovimientoStock.fecha_hora.desc()).limit(100)).scalars().all()
    usuarios = UsuarioRepository(db).listar()
    modal_error = request.query_params.get("error_producto")
    modal_success = request.query_params.get("success_producto")
    return templates.TemplateResponse(request, "productos.html", {
        "productos": productos,
        "movimientos": movimientos,
        "usuarios": usuarios,
        "q": q,
        "modal_error_producto": modal_error,
        "modal_success_producto": modal_success,
        "username": request.session.get("username"),
        "rol": request.session.get("rol"),
    })


@router.post("/productos")
def crear_producto(
    request: Request,
    nombre: str = Form(...),
    marca: str = Form(...),
    referencia: str = Form(...),
    precio_compra: Decimal = Form(...),
    precio: Decimal = Form(...),
    stock: int = Form(0),
    db: Session = Depends(get_db),
):
    if precio_compra < 0:
        return RedirectResponse(
            url=f"/productos?error_producto={quote('El precio de compra no puede ser negativo')}",
            status_code=303,
        )
    if precio < 1:
        return RedirectResponse(
            url=f"/productos?error_producto={quote('El precio de venta debe ser mayor a cero')}",
            status_code=303,
        )
    if stock < 0:
        return RedirectResponse(
            url=f"/productos?error_producto={quote('El stock no puede ser negativo')}",
            status_code=303,
        )
    try:
        repo = ProductoRepository(db)
        repo.crear(nombre, marca, referencia, precio_compra, precio, stock)
    except Exception:
        return RedirectResponse(
            url=f"/productos?error_producto={quote('Error al crear el producto. Verifica los datos e intenta de nuevo.')}",
            status_code=303,
        )
    return RedirectResponse(
        url=f"/productos?success_producto={quote('Producto creado correctamente')}",
        status_code=303,
    )


@router.post("/productos/{producto_id}/editar")
def editar_producto(
    producto_id: int,
    request: Request,
    nombre: str = Form(...),
    marca: str = Form(...),
    referencia: str = Form(...),
    precio_compra: Decimal = Form(...),
    precio: Decimal = Form(...),
    db: Session = Depends(get_db),
):
    if precio_compra < 0:
        return RedirectResponse(
            url=f"/productos?error_producto={quote('El precio de compra no puede ser negativo')}",
            status_code=303,
        )
    if precio < 1:
        return RedirectResponse(
            url=f"/productos?error_producto={quote('El precio de venta debe ser mayor a cero')}",
            status_code=303,
        )
    repo = ProductoRepository(db)
    producto = repo.actualizar(producto_id, nombre, marca, referencia, precio_compra, precio)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return RedirectResponse(
        url=f"/productos?success_producto={quote('Producto actualizado correctamente')}",
        status_code=303,
    )


@router.post("/productos/{producto_id}/ajustar-stock")
def ajustar_stock(
    producto_id: int,
    request: Request,
    cantidad: int = Form(...),
    tipo: str = Form(...),
    tipo_inventario: str = Form("fisico"),
    motivo: str = Form(...),
    db: Session = Depends(get_db),
):
    repo = ProductoRepository(db)
    producto = repo.obtener(producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    if tipo not in ("compra", "ajuste"):
        return RedirectResponse(
            url=f"/productos?error_producto={quote('Tipo de movimiento inválido')}",
            status_code=303,
        )

    if cantidad == 0 or (tipo == "compra" and cantidad < 0):
        return RedirectResponse(
            url=f"/productos?error_producto={quote('Cantidad inválida para el tipo de movimiento')}",
            status_code=303,
        )

    stock_anterior = producto.stock
    stock_comprometido_anterior = producto.stock_comprometido
    
    if tipo_inventario == "comprometido":
        producto.stock_comprometido += cantidad
    else:
        producto.stock += cantidad

    db.add(MovimientoStock(
        producto_id=producto.id,
        cantidad=cantidad,
        stock_anterior=stock_anterior,
        stock_nuevo=producto.stock,
        stock_comprometido_anterior=stock_comprometido_anterior,
        stock_comprometido_nuevo=producto.stock_comprometido,
        tipo=tipo,
        motivo=motivo,
        usuario=request.session.get("username", ""),
        fecha_hora=datetime.now(),
    ))
    db.commit()

    msg = "Stock ajustado correctamente"
    if tipo == "compra":
        msg = "Compra registrada correctamente"
    return RedirectResponse(
        url=f"/productos?success_producto={quote(msg)}",
        status_code=303,
    )
