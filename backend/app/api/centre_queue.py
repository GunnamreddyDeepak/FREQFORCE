from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.queue import (
    CallNextRequest,
    CentreQueueResponse,
    CheckInRequest,
    CheckInResponse,
    QueueEntryResponse,
    QueueStatusUpdateRequest,
)
from app.services.check_in import gate_check_in
from app.services.queue import (
    call_next_queue_entry,
    get_centre_queue,
    update_queue_entry_status,
)

router = APIRouter(
    prefix="/api/v1/centres",
    tags=["Centre Queue & Check-In"],
)


@router.post(
    "/{centre_id}/check-in",
    response_model=CheckInResponse,
    status_code=status.HTTP_200_OK,
    summary="Physical gate check-in for arriving farmers",
)
def check_in_farmer(
    centre_id: UUID,
    check_in_data: CheckInRequest,
    db: Session = Depends(get_db),
) -> CheckInResponse:
    """Verify arrival token and place farmer into centre yard queue."""
    return gate_check_in(
        db=db,
        centre_id=centre_id,
        check_in_data=check_in_data,
    )


@router.get(
    "/{centre_id}/queue",
    response_model=CentreQueueResponse,
    status_code=status.HTTP_200_OK,
    summary="Get operational yard queue with dynamic positions",
)
def list_centre_queue(
    centre_id: UUID,
    date: date = Query(..., description="Queue operational date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
) -> CentreQueueResponse:
    """Return active yard queue with dynamically computed positions and counts."""
    return get_centre_queue(
        db=db,
        centre_id=centre_id,
        queue_date=date,
    )


@router.post(
    "/{centre_id}/queue/call-next",
    response_model=QueueEntryResponse,
    status_code=status.HTTP_200_OK,
    summary="Operator call next waiting farmer",
)
def call_next(
    centre_id: UUID,
    request_data: CallNextRequest,
    db: Session = Depends(get_db),
) -> QueueEntryResponse:
    """Summon the highest-priority currently callable WAITING entry using SKIP LOCKED."""
    return call_next_queue_entry(
        db=db,
        centre_id=centre_id,
        request_data=request_data,
    )


@router.post(
    "/{centre_id}/queue/{queue_entry_id}/status",
    response_model=QueueEntryResponse,
    status_code=status.HTTP_200_OK,
    summary="Update queue entry status",
)
def update_status(
    centre_id: UUID,
    queue_entry_id: UUID,
    update_data: QueueStatusUpdateRequest,
    db: Session = Depends(get_db),
) -> QueueEntryResponse:
    """Update floor operational status (PROCESSING, COMPLETED, NO_SHOW, etc.)."""
    return update_queue_entry_status(
        db=db,
        centre_id=centre_id,
        queue_entry_id=queue_entry_id,
        update_data=update_data,
    )
