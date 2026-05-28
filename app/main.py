import bcrypt
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import engine, SessionLocal, Base
from app.repositories import UsuarioRepository
from app.dependencies import require_session, require_admin
from app.middleware import CSRFProtectionMiddleware

limiter = Limiter(key_func=get_remote_address, default_limits=[])


def crear_o_actualizar_admin(db: Session):
    repo = UsuarioRepository(db)
    print(f"DEBUG: Configurando admin. Username: '{settings.admin_username}', Password len: {len(settings.admin_password)}")
    admin = repo.obtener_por_username(settings.admin_username)
    hash_pw = bcrypt.hashpw(settings.admin_password.encode(), bcrypt.gensalt()).decode()
    
    if admin:
        print(f"DEBUG: Usuario '{settings.admin_username}' ya existe. Sincronizando contraseña...")
        admin.rol = "admin"
        admin.password_hash = hash_pw
    else:
        print(f"DEBUG: Creando nuevo usuario administrador: '{settings.admin_username}'")
        repo.crear(settings.admin_username, hash_pw, "admin")
    db.commit()
    print("DEBUG: Sincronización de admin completada.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        crear_o_actualizar_admin(db)
    finally:
        db.close()
    yield


app = FastAPI(title="Ventas Zapatillas", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(CSRFProtectionMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.get_secret_key(),
    max_age=None,
    https_only=settings.https_only,
    same_site="strict",
)

from app.routers import auth, clientes, productos, ventas, usuarios, reportes
app.include_router(auth.router)
app.include_router(clientes.router, dependencies=[Depends(require_session)])
app.include_router(productos.router, dependencies=[Depends(require_session)])
app.include_router(ventas.router, dependencies=[Depends(require_session)])
app.include_router(reportes.router, dependencies=[Depends(require_session)])
app.include_router(usuarios.router, dependencies=[Depends(require_session), Depends(require_admin)])
