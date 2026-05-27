from fastapi import Request, HTTPException
from starlette.responses import RedirectResponse


async def require_session(request: Request):
    if not request.session.get("username"):
        raise HTTPException(status_code=303, headers={"Location": "/login"})


async def require_admin(request: Request):
    if request.session.get("rol") != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
