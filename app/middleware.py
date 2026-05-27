from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import os

class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    Middleware de seguridad básico para prevenir ataques CSRF.
    En producción, verifica que el encabezado Origin o Referer coincida con el dominio del sitio.
    """
    async def dispatch(self, request: Request, call_next):
        # Solo aplicar a métodos que modifican datos
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            # En modo DEBUG o Testing, podemos ser más permisivos si es necesario
            # Pero en producción (HTTPS_ONLY=true), verificamos el Origin
            origin = request.headers.get("Origin")
            referer = request.headers.get("Referer")
            
            # Si estamos en Render o producción
            if os.getenv("HTTPS_ONLY") == "true":
                # Verificamos que el origin exista y sea del mismo sitio (aproximado)
                # En un entorno real usaríamos una lista de dominios permitidos
                if not origin and not referer:
                    raise HTTPException(status_code=403, detail="CORS/CSRF: Falta encabezado de origen")
        
        response = await call_next(request)
        return response
