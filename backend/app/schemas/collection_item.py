"""Collection item schemas, in the shape frontend/src/api/collections.js uses
(not docs/api-contract.md section 2: /collection-items, slugs, page_size)."""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

Gallery = Literal["main_hall", "telegraph", "monster_mine", "encounter_bay"]
Category = Literal["mineral", "instrument", "document", "photograph", "machinery"]
PublishStatus = Literal["draft", "published"]


class ExhibitionRef(BaseModel):
    id: int
    title: str
    slug: str


class CollectionItemOut(BaseModel):
    id: int
    slug: str
    title: str
    accession_number: Optional[str]
    description: Optional[str]
    category: Optional[str]
    gallery: Optional[str]
    period_text: Optional[str]
    year_from: Optional[int]
    year_to: Optional[int]
    materials: Optional[str]
    image_url: Optional[str]
    exhibition_id: Optional[int]
    is_family_friendly: bool
    is_highlight: bool
    status: str


class CollectionItemDetailOut(CollectionItemOut):
    exhibition: Optional[ExhibitionRef]


class CollectionItemListOut(BaseModel):
    items: list[CollectionItemOut]
    total: int
    page: int
    page_size: int


class StaffCollectionItemListOut(BaseModel):
    items: list[CollectionItemDetailOut]
    total: int


class CollectionItemIn(BaseModel):
    """POST /api/staff/collection-items, as CollectionItemEditor.jsx sends it.
    A draft only needs a title; publishing needs the fields visitors see."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=150)
    accession_number: Optional[str] = Field(default=None, max_length=40)
    description: Optional[str] = Field(default=None, max_length=5000)
    category: Optional[Category] = None
    gallery: Optional[Gallery] = None
    period_text: Optional[str] = Field(default=None, max_length=100)
    year_from: Optional[int] = Field(default=None, ge=0, le=2100)
    year_to: Optional[int] = Field(default=None, ge=0, le=2100)
    materials: Optional[str] = Field(default=None, max_length=200)
    exhibition_id: Optional[int] = None
    is_family_friendly: bool = False
    is_highlight: bool = False
    status: PublishStatus = "draft"

    @model_validator(mode="after")
    def _check(self):
        if self.year_from is not None and self.year_to is not None and self.year_to < self.year_from:
            raise ValueError("year_to must not be earlier than year_from")
        if self.status == "published":
            missing = [name for name in ("accession_number", "description", "category", "gallery")
                       if not getattr(self, name)]
            if missing:
                raise ValueError(f"To publish, fill in: {', '.join(missing)}")
        return self


class CollectionItemPatch(BaseModel):
    """PATCH /api/staff/collection-items/{id}: any subset of the fields."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: Optional[str] = Field(default=None, min_length=1, max_length=150)
    accession_number: Optional[str] = Field(default=None, max_length=40)
    description: Optional[str] = Field(default=None, max_length=5000)
    category: Optional[Category] = None
    gallery: Optional[Gallery] = None
    period_text: Optional[str] = Field(default=None, max_length=100)
    year_from: Optional[int] = Field(default=None, ge=0, le=2100)
    year_to: Optional[int] = Field(default=None, ge=0, le=2100)
    materials: Optional[str] = Field(default=None, max_length=200)
    exhibition_id: Optional[int] = None
    is_family_friendly: Optional[bool] = None
    is_highlight: Optional[bool] = None
    status: Optional[PublishStatus] = None
