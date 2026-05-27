from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories import ClienteRepository
from app.templating import templates

router = APIRouter()


@router.get("/clientes")
def listar_clientes(request: Request, db: Session = Depends(get_db), q: str = ""):
    repo = ClienteRepository(db)
    clientes = repo.listar(q)
    return templates.TemplateResponse(request, "clientes.html", {
        "clientes": clientes,
        "q": q,
        "username": request.session.get("username"),
        "rol": request.session.get("rol"),
    })


@router.post("/clientes")
def crear_cliente(
    request: Request,
    nombre: str = Form(...),
    telefono: str = Form(...),
    direccion: str = Form(None),
    db: Session = Depends(get_db),
):
    repo = ClienteRepository(db)
    repo.crear(nombre, telefono, direccion)
    return RedirectResponse(url="/clientes", status_code=303)


@router.post("/clientes/{cliente_id}/editar")
def editar_cliente(
    cliente_id: int,
    request: Request,
    nombre: str = Form(...),
    telefono: str = Form(...),
    direccion: str = Form(None),
    db: Session = Depends(get_db),
):
    repo = ClienteRepository(db)
    cliente = repo.actualizar(cliente_id, nombre, telefono, direccion)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return RedirectResponse(url="/clientes", status_code=303)
