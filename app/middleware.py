from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import os

class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    Middleware de seguridad básico para prevenir ataques CSRF.
    En producción, verifica que el encabezado Origin o Referer coincida con el dominio del sitio.
    """
    async def dispatch(self, request: Request, call_next):
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            origin = request.headers.get("Origin")
            referer = request.headers.get("Referer")
            host = request.headers.get("Host", "")
            
            is_valid = False
            if origin and host in origin:
                is_valid = True
            elif referer and host in referer:
                is_valid = True
                
            if not is_valid:
                raise HTTPException(status_code=403, detail="CORS/CSRF: Origen de la solicitud no permitido")
        
        response = await call_next(request)
        return response
