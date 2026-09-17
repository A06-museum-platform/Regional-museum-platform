"""
Staff content management for exhibitions.
POST/PUT/DELETE /exhibitions -> FR-10
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models.exhibition import Exhibition
from app.models.user import User, UserRole
from app.schemas.exhibition import ExhibitionCreate, ExhibitionOut, ExhibitionUpdate

router = APIRouter(prefix="/exhibitions", tags=["exhibitions-admin"])


@router.post("", response_model=ExhibitionOut, status_code=status.HTTP_201_CREATED)
def create_exhibition(
    payload: ExhibitionCreate,
    db: Session = Depends(get_db),
    _staff: User = Depends(require_role(UserRole.STAFF, UserRole.ADMINISTRATOR)),
):
    exhibition = Exhibition(**payload.model_dump())
    db.add(exhibition)
    db.commit()
    db.refresh(exhibition)
    return exhibition


@router.put("/{exhibition_id}", response_model=ExhibitionOut)
def update_exhibition(
    exhibition_id: str,
    payload: ExhibitionUpdate,
    db: Session = Depends(get_db),
    _staff: User = Depends(require_role(UserRole.STAFF, UserRole.ADMINISTRATOR)),
):
    exhibition = db.get(Exhibition, exhibition_id)
    if not exhibition:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exhibition not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(exhibition, field, value)
    db.commit()
    db.refresh(exhibition)
    return exhibition


@router.delete("/{exhibition_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exhibition(
    exhibition_id: str,
    db: Session = Depends(get_db),
    _staff: User = Depends(require_role(UserRole.STAFF, UserRole.ADMINISTRATOR)),
):
    exhibition = db.get(Exhibition, exhibition_id)
    if not exhibition:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exhibition not found")
    db.delete(exhibition)
    db.commit()
    return None
