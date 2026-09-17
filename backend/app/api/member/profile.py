"""
Member-only profile actions. GET /auth/me
(URL kept under /auth to match the frozen API contract; only the file's
location changed so it sits with the other member-only endpoints.)
"""
from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.auth import UserOut

router = APIRouter(prefix="/auth", tags=["profile"])


@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user
