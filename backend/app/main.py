import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.admin.members import router as admin_members_router
from app.api.admin.memberships import router as admin_memberships_router
from app.api.admin.users import router as admin_users_router
from app.api.member.membership import router as member_membership_router
from app.api.public.auth import router as auth_router
from app.api.public.collections import router as collections_router
from app.api.public.membership_plans import router as membership_plans_router
from app.api.staff.media import router as staff_media_router
from app.core.config import get_settings
from app.core.errors import ApiError, api_error_handler
from app.db.session import get_session

app = FastAPI(title="Museum Platform API")
app.add_exception_handler(ApiError, api_error_handler)
app.include_router(auth_router)
app.include_router(membership_plans_router)
app.include_router(collections_router)
app.include_router(member_membership_router)
app.include_router(staff_media_router)
app.include_router(admin_users_router)
app.include_router(admin_memberships_router)
app.include_router(admin_members_router)

# Local-fallback file serving (MEDIA_BACKEND=local). The directory lives
# on the uploads-data docker volume. check_dir=False (rather than a
# try/except that would permanently skip the route): the mount always
# exists, and LocalStorage creates the directory on first upload, so files
# uploaded later are served instead of 404ing.
Path(get_settings().local_upload_dir).mkdir(parents=True, exist_ok=True)
app.mount(
    "/uploads",
    StaticFiles(directory=get_settings().local_upload_dir, check_dir=False),
    name="uploads",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(dict.fromkeys(["http://localhost:5173", get_settings().frontend_origin])),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    # Render and Compose use this liveness probe; DB outages must not restart us.
    return {"status": "ok"}


async def _check_database():
    # Include session creation and cleanup in the readiness timeout/error handling.
    async with asynccontextmanager(get_session)() as session:
        await session.execute(text("SELECT 1"))


@app.get("/api/health")
async def api_health():
    try:
        await asyncio.wait_for(_check_database(), timeout=2.0)
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "database": "unavailable", "service": "museum-api"},
        )
    return {"status": "ok", "database": "ok", "service": "museum-api"}
