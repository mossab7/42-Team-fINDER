from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import get_settings
from app.core.database import init_db
from app.services.scanner import recover_interrupted_scans
from app.services.auth import SESSION_COOKIE, current_user
from app.core.database import SessionLocal
from app.models.database import Notification, utcnow
from sqlalchemy import delete, update


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    # Retention is enforced even when nobody opens the notifications page.
    async with SessionLocal() as session:
        await session.execute(delete(Notification).where((Notification.created_at < utcnow() - timedelta(days=5)) | (Notification.type != "match")))
        # Remove legacy user-entered profile data. Only 42-sourced identity is
        # retained to associate an authenticated student with their swipes.
        from app.models.database import StudentProfile
        await session.execute(update(StudentProfile).values(biography="", skills=[], languages=[], availability="", working_hours="", github_url=None, visible=True))
        await session.commit()
    await recover_interrupted_scans()
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def require_42_login(request: Request, call_next):
    """Protect all data routes while leaving health and OAuth handshakes usable."""
    if not settings.auth_required or not request.url.path.startswith("/api/"):
        return await call_next(request)
    public_paths = {"/api/health", "/api/auth/login", "/api/auth/callback", "/api/auth/me"}
    if request.url.path in public_paths:
        return await call_next(request)
    async with SessionLocal() as session:
        user = await current_user(session, request.cookies.get(SESSION_COOKIE))
    if not user:
        return JSONResponse(status_code=401, content={"detail": "Sign in with a 42 student account to access this resource."})
    request.state.auth_user = user
    return await call_next(request)
app.include_router(router)


@app.get("/")
async def root():
    return {"name": settings.app_name, "docs": "/docs", "health": "/api/health"}
