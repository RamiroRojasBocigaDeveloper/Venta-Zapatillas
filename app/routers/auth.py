import bcrypt
import time
from typing import Optional
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.repositories import UsuarioRepository
from app.templating import templates
from app.limiter import limiter

router = APIRouter()


@router.get("/login")
def login_form(request: Request, error: Optional[str] = None):
    return templates.TemplateResponse(request, "login.html", {"error": error})


@router.post("/login")
@limiter.limit("10/minute")
def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    repo = UsuarioRepository(db)
    usuario = repo.obtener_por_username(username)
    if not usuario or not bcrypt.checkpw(password.encode(), usuario.password_hash.encode()):
        return templates.TemplateResponse(request, "login.html", {"error": "Usuario o contraseña incorrectos"})
    request.session["username"] = username
    request.session["rol"] = usuario.rol
    request.session["last_activity"] = time.time()
    return RedirectResponse(url="/", status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)
