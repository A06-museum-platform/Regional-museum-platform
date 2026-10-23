"""Visitor information ("Plan your visit"; docs/api-contract.md section 10;
role-permission matrix: "Update visitor information pages" -- Staff).

museum_information holds the museum's address and how to get there;
facility holds one row per facility or accessibility service."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class FacilityOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    location: Optional[str]
    accessibility_info: Optional[str]
    is_available: bool


class VisitorInformationOut(BaseModel):
    museum_name: str
    address: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    transport: Optional[str]
    parking: Optional[str]
    about: Optional[str]
    facilities: list[FacilityOut]


class FacilityIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=1000)
    location: Optional[str] = Field(default=None, max_length=100)
    accessibility_info: Optional[str] = Field(default=None, max_length=1000)
    is_available: bool = True


class VisitorInformationIn(BaseModel):
    """PUT /api/staff/visitor-information: the whole page, facilities included
    (the list replaces the stored one, in the order given)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    museum_name: str = Field(min_length=1, max_length=150)
    address: str = Field(min_length=1, max_length=500)
    phone: Optional[str] = Field(default=None, max_length=20)
    email: Optional[EmailStr] = None
    transport: Optional[str] = Field(default=None, max_length=2000)
    parking: Optional[str] = Field(default=None, max_length=2000)
    about: Optional[str] = Field(default=None, max_length=4000)
    facilities: list[FacilityIn] = Field(default_factory=list, max_length=30)
