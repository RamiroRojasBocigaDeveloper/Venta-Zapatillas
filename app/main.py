import bcrypt
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.limiter import limiter

from app.config import settings
from app.database import engine, SessionLocal, Base
from app.repositories import UsuarioRepository
from app.dependencies import require_session, require_admin
from app.middleware import CSRFProtectionMiddleware


def crear_o_actualizar_admin(db: Session):
    repo = UsuarioRepository(db)
    print(f"DEBUG: Configurando admin. Username: '{settings.admin_username}', Password len: {len(settings.admin_password)}")
    admin = repo.obtener_por_username(settings.admin_username)
    hash_pw = bcrypt.hashpw(settings.admin_password.encode(), bcrypt.gensalt()).decode()
    
    if admin:
        print(f"DEBUG: Usuario '{settings.admin_username}' ya existe. Conservando su clave y roles guardados.")
    else:
        print(f"DEBUG: Creando nuevo usuario administrador: '{settings.admin_username}'")
        repo.crear(settings.admin_username, hash_pw, "admin")
    db.commit()
    print("DEBUG: Sincronización de admin completada.")


def run_migrations():
    """Aplica migraciones estructurales de forma segura en cada arranque."""
    db_url = str(engine.url)
    is_mysql = db_url.startswith("mysql")

    migrations = [
        # tabla, columna, definición SQL
        ("movimientos_stock", "stock_comprometido_anterior", "INTEGER NOT NULL DEFAULT 0"),
        ("movimientos_stock", "stock_comprometido_nuevo",    "INTEGER NOT NULL DEFAULT 0"),
        ("pagos",             "cobrado_por",                 "VARCHAR(100) NOT NULL DEFAULT ''"),
        ("ventas_eliminadas", "total_pagado_reembolsado",    "DECIMAL(14,2) NOT NULL DEFAULT 0"),
    ]

    with engine.connect() as conn:
        for tabla, columna, definicion in migrations:
            try:
                if is_mysql:
                    # MySQL soporta IF NOT EXISTS en ALTER TABLE
                    conn.execute(
                        __import__("sqlalchemy").text(
                            f"ALTER TABLE {tabla} ADD COLUMN IF NOT EXISTS {columna} {definicion}"
                        )
                    )
                else:
                    # SQLite no soporta IF NOT EXISTS → lo intentamos y si falla es porque ya existe
                    conn.execute(
                        __import__("sqlalchemy").text(
                            f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}"
                        )
                    )
                conn.commit()
                print(f"MIGRATION OK: {tabla}.{columna}")
            except Exception as e:
                # La columna ya existe → ignorar
                print(f"MIGRATION SKIP: {tabla}.{columna} ({e.__class__.__name__})")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    run_migrations()
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
