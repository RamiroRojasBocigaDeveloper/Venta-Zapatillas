import os
from urllib.parse import urlparse
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware


def _normalize_host(host: str) -> str:
    """Normaliza el host eliminando puerto estándar para comparación segura."""
    # Soporta 'host:port' → quita el puerto si es 80 o 443
    if ":" in host:
        h, port = host.rsplit(":", 1)
        if port in ("80", "443"):
            return h
    return host


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    Middleware de seguridad para prevenir ataques CSRF.
    Verifica que Origin/Referer coincida exactamente con el Host del servidor.
    Permite localhost y 127.0.0.1 en desarrollo.
    """
    SAFE_LOCAL = {"localhost", "127.0.0.1", "0.0.0.0"}

    async def dispatch(self, request: Request, call_next):
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            origin = request.headers.get("Origin")
            referer = request.headers.get("Referer")
            raw_host = request.headers.get("Host", "")
            host = _normalize_host(raw_host)

            # Permitir localhost sin restricciones (entorno de desarrollo)
            host_base = host.split(":")[0]
            if host_base in self.SAFE_LOCAL:
                return await call_next(request)

            is_valid = False
            if origin:
                origin_host = _normalize_host(urlparse(origin).netloc)
                is_valid = origin_host == host
            elif referer:
                referer_host = _normalize_host(urlparse(referer).netloc)
                is_valid = referer_host == host

            if not is_valid:
                raise HTTPException(status_code=403, detail="CORS/CSRF: Origen de la solicitud no permitido")

        response = await call_next(request)
        return response
