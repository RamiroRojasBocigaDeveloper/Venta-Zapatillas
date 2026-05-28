from fastapi import Request, HTTPException
from starlette.responses import RedirectResponse
import time

async def require_session(request: Request):
    if not request.session.get("username"):
        raise HTTPException(status_code=303, headers={"Location": "/login"})
        
    now = time.time()
    last_activity = request.session.get("last_activity")
    if last_activity and (now - last_activity > 900):
        request.session.clear()
        raise HTTPException(status_code=303, headers={"Location": "/login?error=Sesion+cerrada+por+inactividad"})
        
    request.session["last_activity"] = now



async def require_admin(request: Request):
    if request.session.get("rol") != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
