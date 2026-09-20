from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.staff.media import router as staff_media_router
from app.core.errors import ApiError, api_error_handler

app = FastAPI(title="Museum Platform API")
app.add_exception_handler(ApiError, api_error_handler)
app.include_router(staff_media_router)

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