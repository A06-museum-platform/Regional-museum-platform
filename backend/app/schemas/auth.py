"""Pydantic schemas for the login flow (docs/api-contract.md section 1)."""

from pydantic import BaseModel, EmailStr

from app.schemas.user import UserOut


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
