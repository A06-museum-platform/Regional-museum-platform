"""Shared response shapes from docs/api-contract.md conventions."""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Every list response: { items, total, page, size }."""

    items: list[T]
    total: int
    page: int
    size: int
