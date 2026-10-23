"""Visitor information: one museum_information row (locked scope: one
museum) and its facility rows. Staff replace the whole page in one save."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.schemas.visitor_information import (
    FacilityOut,
    VisitorInformationIn,
    VisitorInformationOut,
)

_MUSEUM_ID = "(SELECT MIN(museum_info_id) FROM museum_information)"


async def get_visitor_information(db: AsyncSession) -> VisitorInformationOut:
    museum = (
        await db.execute(
            text("SELECT museum_info_id, museum_name, address, phone, email, transport_info, "
                 f"parking_info, general_info FROM museum_information WHERE museum_info_id = {_MUSEUM_ID}")
        )
    ).first()
    if museum is None:
        raise ApiError(404, "Visitor information has not been set up yet.", "NOT_FOUND")
    facilities = (
        await db.execute(
            text("SELECT facility_id, facility_name, description, location, accessibility_info, "
                 "is_available FROM facility WHERE museum_info_id = :id ORDER BY facility_id"),
            {"id": museum.museum_info_id},
        )
    ).all()
    return VisitorInformationOut(
        museum_name=museum.museum_name,
        address=museum.address,
        phone=museum.phone,
        email=museum.email,
        transport=museum.transport_info,
        parking=museum.parking_info,
        about=museum.general_info,
        facilities=[
            FacilityOut(id=f.facility_id, name=f.facility_name, description=f.description,
                        location=f.location, accessibility_info=f.accessibility_info,
                        is_available=f.is_available)
            for f in facilities
        ],
    )


async def save_visitor_information(db: AsyncSession, body: VisitorInformationIn) -> VisitorInformationOut:
    museum_id = (await db.execute(text(f"SELECT {_MUSEUM_ID}"))).scalar_one_or_none()
    values = {"name": body.museum_name, "address": body.address, "phone": body.phone or None,
              "email": body.email or None, "transport": body.transport or None,
              "parking": body.parking or None, "about": body.about or None}
    if museum_id is None:
        museum_id = (
            await db.execute(
                text("INSERT INTO museum_information (museum_name, address, phone, email, transport_info, "
                     "parking_info, general_info) VALUES (:name, :address, :phone, :email, :transport, "
                     ":parking, :about) RETURNING museum_info_id"),
                values,
            )
        ).scalar_one()
    else:
        await db.execute(
            text("UPDATE museum_information SET museum_name = :name, address = :address, phone = :phone, "
                 "email = :email, transport_info = :transport, parking_info = :parking, "
                 "general_info = :about WHERE museum_info_id = :id"),
            {**values, "id": museum_id},
        )
    await db.execute(text("DELETE FROM facility WHERE museum_info_id = :id"), {"id": museum_id})
    for facility in body.facilities:
        await db.execute(
            text("INSERT INTO facility (museum_info_id, facility_name, description, location, "
                 "accessibility_info, is_available) VALUES (:id, :name, :description, :location, "
                 ":access, :available)"),
            {"id": museum_id, "name": facility.name, "description": facility.description or None,
             "location": facility.location or None, "access": facility.accessibility_info or None,
             "available": facility.is_available},
        )
    await db.commit()
    return await get_visitor_information(db)
