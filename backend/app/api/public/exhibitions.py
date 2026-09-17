"""
Public, read-only exhibition browsing.
GET /exhibitions -> FR-01 (list, filterable by status)
GET /exhibitions/{id} -> FR-02 (detail)
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.exhibition import Exhibition, ExhibitionStatus
from app.schemas.common import PaginatedResponse
from app.schemas.exhibition import ExhibitionOut

router = APIRouter(prefix="/exhibitions", tags=["exhibitions"])


@router.get("", response_model=PaginatedResponse[ExhibitionOut])
def list_exhibitions(
    status_filter: ExhibitionStatus | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Exhibition)
    if status_filter:
        query = query.filter(Exhibition.status == status_filter)

    total = query.count()
    items = (
        query.order_by(Exhibition.start_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{exhibition_id}", response_model=ExhibitionOut)
def get_exhibition(exhibition_id: str, db: Session = Depends(get_db)):
    exhibition = db.get(Exhibition, exhibition_id)
    if not exhibition:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exhibition not found")
    return exhibition
