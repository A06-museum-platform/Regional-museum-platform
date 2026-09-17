"""
Auth + RBAC dependencies.

Usage in a router:

    @router.get("/admin/users")
    def list_users(current_user: User = Depends(require_role(UserRole.ADMINISTRATOR))):
        ...

    @router.put("/exhibitions/{id}")
    def update_exhibition(
        current_user: User = Depends(require_role(UserRole.STAFF, UserRole.ADMINISTRATOR)),
    ):
        ...

IMPORTANT (risk table item — "access control gaps"): every staff/admin-only
route MUST declare one of these dependencies. Hiding a button in the React
UI is not access control; the check has to live here, server-side.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User, UserRole

# tokenUrl is just where /docs points the "Authorize" button at -- the
# actual login endpoint is POST /auth/login and returns access+refresh tokens.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise CREDENTIALS_EXCEPTION
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise CREDENTIALS_EXCEPTION
    except JWTError:
        raise CREDENTIALS_EXCEPTION

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise CREDENTIALS_EXCEPTION
    return user


def require_role(*allowed_roles: UserRole):
    """
    Dependency factory. Any route can require one or more roles:
        Depends(require_role(UserRole.STAFF, UserRole.ADMINISTRATOR))
    """
    def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return _check
