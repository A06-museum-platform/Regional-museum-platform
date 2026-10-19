"""Pydantic schemas for public collection items, in the shape
frontend/src/api/collections.js requests (not docs/api-contract.md
section 2 -- see app/services/collection_service.py)."""

from typing import Optional

from pydantic import BaseModel


class ExhibitionRef(BaseModel):
    id: int
    title: str
    slug: str


class CollectionItemOut(BaseModel):
    id: int
    slug: str
    title: str
    description: Optional[str]
    period_text: Optional[str]
    is_highlight: bool
    image_url: Optional[str]
    exhibition_id: Optional[int]
    status: str
    # No columns for these in collection_item yet; see collection_service.
    category: str
    gallery: Optional[str]
    accession_number: Optional[str]
    materials: Optional[str]
    year_from: Optional[int]
    year_to: Optional[int]
    is_family_friendly: Optional[bool]


class CollectionItemDetailOut(CollectionItemOut):
    exhibition: Optional[ExhibitionRef]


class CollectionItemListOut(BaseModel):
    items: list[CollectionItemOut]
    total: int
    page: int
    page_size: int
