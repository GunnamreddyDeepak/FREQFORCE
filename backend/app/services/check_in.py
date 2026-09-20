from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.centre_slot import CentreSlot
from app.models.procurement_request import (
    ProcurementRequest,
    ProcurementRequestStatus,
)
from app.models.queue_entry import QueueEntry, QueueStatus
from app.models.token import Token, TokenStatus
from app.schemas.queue import CheckInRequest, CheckInResponse
from app.services.procurement_request_state import (
    transition_procurement_request,
)


def calculate_dynamic_position(
    db: Session,
    centre_id: UUID,
    queue_entry_id: UUID,
    query_date: Optional[datetime.date] = None,
) -> int:
    """Compute the 1-based dynamic queue position for a waiting queue entry."""
    subq = (
        db.query(
            QueueEntry.id.label("entry_id"),
            func.row_number()
            .over(
                order_by=[
                    QueueEntry.is_late.asc(),
                    CentreSlot.start_time.asc(),
                    QueueEntry.check_in_time.asc(),
                    Token.token_number.asc(),
                ]
            )
            .label("pos"),
        )
        .join(Token, QueueEntry.token_id == Token.id)
        .join(CentreSlot, QueueEntry.slot_id == CentreSlot.id)
        .filter(
            QueueEntry.centre_id == centre_id,
            QueueEntry.status == QueueStatus.WAITING.value,
        )
    )
    if query_date is not None:
        subq = subq.filter(Token.token_date == query_date)

    subquery = subq.subquery()
    pos = db.query(subquery.c.pos).filter(subquery.c.entry_id == queue_entry_id).scalar()
    return int(pos) if pos is not None else 1


def gate_check_in(
    db: Session,
    centre_id: UUID,
    check_in_data: CheckInRequest,
    check_in_time_override: Optional[datetime] = None,
) -> CheckInResponse:
    """Perform physical gate check-in for arriving farmers.

    Enforces ascending partial lock order:
    1. ProcurementRequest (FOR UPDATE)
    2. Token (FOR UPDATE)
    """
    # 1. Lookup Token by token_number
    token_preview = (
        db.query(Token)
        .filter(Token.token_number == check_in_data.token_number)
        .first()
    )
    if token_preview is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Token '{check_in_data.token_number}' not found",
        )

    if token_preview.centre_id != centre_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token does not belong to this procurement centre",
        )

    # 2. Lock ProcurementRequest (Rank 1)
    procurement_request = (
        db.query(ProcurementRequest)
        .filter(ProcurementRequest.id == token_preview.procurement_request_id)
        .with_for_update()
        .first()
    )
    if procurement_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procurement request not found",
        )

    # 3. Lock Token (Rank 5)
    token = (
        db.query(Token)
        .filter(Token.id == token_preview.id)
        .with_for_update()
        .first()
    )
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found",
        )

    # 4. Check Idempotency
    if (
        token.status == TokenStatus.USED.value
        and procurement_request.status == ProcurementRequestStatus.CHECKED_IN.value
    ):
        existing_entry = (
            db.query(QueueEntry)
            .filter(QueueEntry.token_id == token.id)
            .first()
        )
        if existing_entry is not None:
            slot = (
                db.query(CentreSlot)
                .filter(CentreSlot.id == token.slot_id)
                .first()
            )
            slot_window = (
                f"{slot.start_time.strftime('%H:%M:%S')} - {slot.end_time.strftime('%H:%M:%S')}"
                if slot
                else ""
            )
            dyn_pos = calculate_dynamic_position(
                db=db,
                centre_id=centre_id,
                queue_entry_id=existing_entry.id,
                query_date=token.token_date,
            )
            return CheckInResponse(
                queue_entry_id=existing_entry.id,
                token_number=token.token_number,
                procurement_request_id=procurement_request.id,
                centre_id=centre_id,
                status=existing_entry.status,
                is_late=existing_entry.is_late,
                slot_window=slot_window,
                check_in_time=existing_entry.check_in_time,
                dynamic_position=dyn_pos,
                vehicle_number=existing_entry.vehicle_number,
            )

    if token.status != TokenStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Token is not active (current status: '{token.status}')",
        )

    if procurement_request.status != ProcurementRequestStatus.TOKEN_GENERATED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot check in request in status '{procurement_request.status}'",
        )

    slot = (
        db.query(CentreSlot)
        .filter(CentreSlot.id == token.slot_id)
        .first()
    )
    if slot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Confirmed slot not found",
        )

    check_in_dt = check_in_time_override or datetime.now(timezone.utc)

    # 5. Determine lateness
    # Compare check_in date/time with slot date and end_time
    check_in_date = check_in_dt.date() if hasattr(check_in_dt, "date") else token.token_date
    check_in_time_val = check_in_dt.time() if hasattr(check_in_dt, "time") else check_in_dt

    is_late = False
    if check_in_date > slot.slot_date:
        is_late = True
    elif check_in_date == slot.slot_date:
        if check_in_time_val > slot.end_time:
            is_late = True

    # 6. State Transitions & Queue Creation
    token.status = TokenStatus.USED.value
    transition_procurement_request(
        procurement_request=procurement_request,
        target_status=ProcurementRequestStatus.CHECKED_IN,
        db=db,
    )

    queue_entry = QueueEntry(
        token_id=token.id,
        procurement_request_id=procurement_request.id,
        centre_id=centre_id,
        slot_id=slot.id,
        check_in_time=check_in_dt,
        is_late=is_late,
        vehicle_number=check_in_data.vehicle_number,
        status=QueueStatus.WAITING.value,
    )
    db.add(queue_entry)
    db.flush()

    dyn_pos = calculate_dynamic_position(
        db=db,
        centre_id=centre_id,
        queue_entry_id=queue_entry.id,
        query_date=token.token_date,
    )

    db.commit()
    db.refresh(queue_entry)

    slot_window = (
        f"{slot.start_time.strftime('%H:%M:%S')} - {slot.end_time.strftime('%H:%M:%S')}"
    )

    return CheckInResponse(
        queue_entry_id=queue_entry.id,
        token_number=token.token_number,
        procurement_request_id=procurement_request.id,
        centre_id=centre_id,
        status=queue_entry.status,
        is_late=queue_entry.is_late,
        slot_window=slot_window,
        check_in_time=queue_entry.check_in_time,
        dynamic_position=dyn_pos,
        vehicle_number=queue_entry.vehicle_number,
    )
