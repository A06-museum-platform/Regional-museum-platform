"""Pydantic schemas for admin user listing (snake_case per API contract)."""

from pydantic import BaseModel


class UserOut(BaseModel):
    id: int
    email: str
    display_name: str
    role: str


class UserListOut(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    size: int
