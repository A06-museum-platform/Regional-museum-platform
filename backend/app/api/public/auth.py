"""Public auth endpoints (docs/api-contract.md sections 1 and 10).

POST /api/auth/login    -> { access_token, token_type, user }
POST /api/auth/register -> 201 { access_token, token_type, user }; the new
                           account is a visitor and is signed straight in
GET  /api/auth/me       -> user (the front end calls it on every page load
                           to restore the session)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import create_access_token
from app.db.session import get_session
from app.schemas.auth import LoginIn, RegisterIn, TokenOut
from app.schemas.user import UserOut
from app.services.auth_service import authenticate, register

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
async def login(
    body: LoginIn,
    db: AsyncSession = Depends(get_session),
):
    user = await authenticate(db, body.email, body.password)
    token = create_access_token(user_id=user.id, role=user.role)
    return TokenOut(access_token=token, user=user)


@router.post("/register", response_model=TokenOut, status_code=201)
async def register_account(
    body: RegisterIn,
    db: AsyncSession = Depends(get_session),
):
    user = await register(db, body)
    token = create_access_token(user_id=user.id, role=user.role)
    return TokenOut(access_token=token, user=user)


@router.get("/me", response_model=UserOut)
async def me(user: UserOut = Depends(get_current_user)):
    return user
