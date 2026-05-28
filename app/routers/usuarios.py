from urllib.parse import quote
import bcrypt
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories import UsuarioRepository
from app.templating import templates
from app.config import settings

router = APIRouter()


@router.get("/usuarios")
def listar_usuarios(request: Request, db: Session = Depends(get_db)):
    repo = UsuarioRepository(db)
    usuarios = repo.listar()
    modal_error = request.query_params.get("error_usuario")
    modal_success = request.query_params.get("success_usuario")
    return templates.TemplateResponse(request, "usuarios.html", {
        "usuarios": usuarios,
        "modal_error_usuario": modal_error,
        "modal_success": modal_success,
        "username": request.session.get("username"),
        "rol": request.session.get("rol"),
        "admin_username": settings.admin_username,
    })


@router.post("/usuarios")
def crear_usuario(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    rol_usuario: str = Form("vendedor"),
    db: Session = Depends(get_db),
):
    repo = UsuarioRepository(db)
    if repo.obtener_por_username(username):
        return RedirectResponse(
            url=f"/usuarios?error_usuario={quote('El usuario ya existe')}",
            status_code=303,
        )
    if len(password) < 6:
        return RedirectResponse(
            url=f"/usuarios?error_usuario={quote('La contraseña debe tener al menos 6 caracteres')}",
            status_code=303,
        )
    try:
        hash_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        repo.crear(username, hash_pw, rol_usuario)
        db.commit()
    except Exception:
        db.rollback()
        return RedirectResponse(
            url=f"/usuarios?error_usuario={quote('Error al crear el usuario. Intenta de nuevo.')}",
            status_code=303,
        )
    return RedirectResponse(
        url=f"/usuarios?success_usuario={quote('Usuario creado correctamente')}",
        status_code=303,
    )


@router.post("/usuarios/{usuario_id}/editar")
def editar_usuario(
    usuario_id: int,
    request: Request,
    rol_usuario: str = Form(...),
    db: Session = Depends(get_db),
):
    repo = UsuarioRepository(db)
    user = repo.actualizar_rol(usuario_id, rol_usuario)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return RedirectResponse(
        url=f"/usuarios?success_usuario={quote('Rol actualizado correctamente')}",
        status_code=303,
    )


@router.post("/usuarios/{usuario_id}/password")
def cambiar_password(
    usuario_id: int,
    request: Request,
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    if len(password) < 6:
        return RedirectResponse(
            url=f"/usuarios?error_usuario={quote('La contraseña debe tener al menos 6 caracteres')}",
            status_code=303,
        )
    repo = UsuarioRepository(db)
    hash_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user = repo.cambiar_password(usuario_id, hash_pw)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return RedirectResponse(
        url=f"/usuarios?success_usuario={quote('Contraseña cambiada correctamente')}",
        status_code=303,
    )


@router.post("/usuarios/{usuario_id}/eliminar")
def eliminar_usuario(usuario_id: int, request: Request, db: Session = Depends(get_db)):
    repo = UsuarioRepository(db)
    user = repo.obtener(usuario_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.username == settings.admin_username:
        return RedirectResponse(
            url=f"/usuarios?error_usuario={quote('No se puede eliminar el administrador principal')}",
            status_code=303,
        )
    repo.eliminar(usuario_id)
    db.commit()
    return RedirectResponse(
        url=f"/usuarios?success_usuario={quote('Usuario eliminado correctamente')}",
        status_code=303,
    )
