"""Pydantic schemas for users and admin user management (snake_case per
API contract)."""

from typing import Literal, Optional

from pydantic import BaseModel

RoleName = Literal["visitor", "member", "staff", "admin"]


class UserOut(BaseModel):
    id: int
    email: str
    display_name: str
    role: str


class AdminUserOut(UserOut):
    """UserOut plus the account status only admins see (section 9)."""

    is_active: bool


class UserListOut(BaseModel):
    items: list[AdminUserOut]
    total: int
    page: int
    size: int


class UserUpdateIn(BaseModel):
    """PATCH /api/users/{id}: any subset of role / is_active."""

    role: Optional[RoleName] = None
    is_active: Optional[bool] = None
