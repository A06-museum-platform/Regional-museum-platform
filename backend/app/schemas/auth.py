"""Pydantic schemas for the login and register flows (docs/api-contract.md
sections 1 and 10)."""

from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserOut


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RegisterIn(BaseModel):
    # Lengths match user_account in 001_initial_schema.sql.
    email: EmailStr = Field(max_length=100)
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    phone: Optional[str] = Field(default=None, max_length=20)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
