from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.staff.media import router as staff_media_router
from app.core.config import get_settings
from app.core.errors import ApiError, api_error_handler

app = FastAPI(title="Museum Platform API")
app.add_exception_handler(ApiError, api_error_handler)
app.include_router(staff_media_router)

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
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/health")
def api_health():
    return {"status": "ok", "service": "museum-api"}