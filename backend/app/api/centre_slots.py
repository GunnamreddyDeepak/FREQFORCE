from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.centre_slot import CentreSlotsResponse
from app.services.centre_slot import get_centre_slots

router = APIRouter(
    prefix="/api/v1/centres",
    tags=["Procurement Centres"],
)


@router.get(
    "/{centre_id}/slots",
    response_model=CentreSlotsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get available centre time slots and capacity",
)
def list_centre_slots(
    centre_id: UUID,
    date: date = Query(..., description="Target procurement date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
) -> CentreSlotsResponse:
    """Return available slot windows and capacity for a centre on a given date."""
    return get_centre_slots(
        db=db,
        centre_id=centre_id,
        slot_date=date,
    )
