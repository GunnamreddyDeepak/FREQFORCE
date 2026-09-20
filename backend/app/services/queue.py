from datetime import date, datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.centre_slot import CentreSlot
from app.models.queue_entry import QueueEntry, QueueStatus
from app.models.token import Token
from app.schemas.queue import (
    CallNextRequest,
    CentreQueueResponse,
    QueueEntryResponse,
    QueueStatusUpdateRequest,
)


VALID_QUEUE_TRANSITIONS: dict[str, set[str]] = {
    QueueStatus.WAITING.value: {
        QueueStatus.CALLED.value,
        QueueStatus.CANCELLED.value,
    },
    QueueStatus.CALLED.value: {
        QueueStatus.PROCESSING.value,
        QueueStatus.NO_SHOW.value,
        QueueStatus.WAITING.value,
        QueueStatus.CANCELLED.value,
    },
    QueueStatus.PROCESSING.value: {
        QueueStatus.COMPLETED.value,
        QueueStatus.CANCELLED.value,
    },
    QueueStatus.NO_SHOW.value: {
        QueueStatus.WAITING.value,
        QueueStatus.CANCELLED.value,
    },
    QueueStatus.COMPLETED.value: set(),
    QueueStatus.CANCELLED.value: set(),
}


def get_centre_queue(
    db: Session,
    centre_id: UUID,
    queue_date: date,
) -> CentreQueueResponse:
    """Retrieve full operational yard queue for a centre and date with dynamic position calculation."""
    # Query all queue entries for the centre and date
    rows = (
        db.query(
            QueueEntry,
            Token.token_number,
            CentreSlot.start_time,
            CentreSlot.end_time,
        )
        .join(Token, QueueEntry.token_id == Token.id)
        .join(CentreSlot, QueueEntry.slot_id == CentreSlot.id)
        .filter(
            QueueEntry.centre_id == centre_id,
            Token.token_date == queue_date,
        )
        .all()
    )

    # Separate WAITING entries to compute dynamic positions deterministically
    waiting_entries = [
        r for r in rows if r[0].status == QueueStatus.WAITING.value
    ]

    # Dynamic sort: is_late ASC, slot.start_time ASC, check_in_time ASC, token_number ASC
    waiting_entries.sort(
        key=lambda r: (
            r[0].is_late,
            r[2],  # slot.start_time
            r[0].check_in_time,
            r[1],  # token_number
        )
    )

    positions_map = {
        r[0].id: pos + 1 for pos, r in enumerate(waiting_entries)
    }

    total_waiting = 0
    total_called = 0
    total_processing = 0
    entry_responses = []

    # Format all entries
    for qe, token_num, start_t, end_t in rows:
        if qe.status == QueueStatus.WAITING.value:
            total_waiting += 1
        elif qe.status == QueueStatus.CALLED.value:
            total_called += 1
        elif qe.status == QueueStatus.PROCESSING.value:
            total_processing += 1

        slot_window = f"{start_t.strftime('%H:%M:%S')} - {end_t.strftime('%H:%M:%S')}"
        dyn_pos = positions_map.get(qe.id)

        entry_responses.append(
            QueueEntryResponse(
                queue_entry_id=qe.id,
                token_number=token_num,
                procurement_request_id=qe.procurement_request_id,
                dynamic_position=dyn_pos,
                status=qe.status,
                is_late=qe.is_late,
                slot_window=slot_window,
                check_in_time=qe.check_in_time,
                called_at=qe.called_at,
                counter_or_bay=qe.counter_or_bay,
                vehicle_number=qe.vehicle_number,
            )
        )

    # Sort final entry responses by dynamic position if waiting, then check_in_time
    entry_responses.sort(
        key=lambda e: (
            0 if e.status == QueueStatus.WAITING.value else 1,
            e.dynamic_position if e.dynamic_position is not None else 999999,
            e.check_in_time,
        )
    )

    return CentreQueueResponse(
        centre_id=centre_id,
        queue_date=queue_date,
        total_waiting=total_waiting,
        total_called=total_called,
        total_processing=total_processing,
        entries=entry_responses,
    )


def call_next_queue_entry(
    db: Session,
    centre_id: UUID,
    request_data: CallNextRequest,
    current_time_override: Optional[datetime] = None,
) -> QueueEntryResponse:
    """Call the highest-priority currently callable WAITING entry using SKIP LOCKED.

    Operational rules:
    - Future-slot farmers MUST NOT be called before their slot_start time.
    - Late entries from expired slots are eligible after their slot has expired.
    - Locks only QueueEntry rows with PostgreSQL FOR UPDATE SKIP LOCKED.
    """
    now_dt = current_time_override or datetime.now(timezone.utc)
    current_time_val = now_dt.time() if hasattr(now_dt, "time") else now_dt

    # Query WAITING entries for this centre where slot has started or is late
    query = (
        db.query(QueueEntry)
        .join(CentreSlot, QueueEntry.slot_id == CentreSlot.id)
        .join(Token, QueueEntry.token_id == Token.id)
        .filter(
            QueueEntry.centre_id == centre_id,
            QueueEntry.status == QueueStatus.WAITING.value,
            # Callable constraint: Either is_late (expired slot) or slot.start_time <= current_time
            (QueueEntry.is_late.is_(True)) | (CentreSlot.start_time <= current_time_val),
        )
        .order_by(
            QueueEntry.is_late.asc(),
            CentreSlot.start_time.asc(),
            QueueEntry.check_in_time.asc(),
            Token.token_number.asc(),
        )
        .with_for_update(of=QueueEntry, skip_locked=True)
    )

    next_entry = query.first()

    if next_entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No callable waiting entries found in queue",
        )

    # Transition to CALLED
    next_entry.status = QueueStatus.CALLED.value
    next_entry.called_at = now_dt
    if request_data.counter_or_bay:
        next_entry.counter_or_bay = request_data.counter_or_bay

    db.commit()
    db.refresh(next_entry)

    token = db.query(Token).filter(Token.id == next_entry.token_id).first()
    slot = db.query(CentreSlot).filter(CentreSlot.id == next_entry.slot_id).first()
    slot_window = (
        f"{slot.start_time.strftime('%H:%M:%S')} - {slot.end_time.strftime('%H:%M:%S')}"
        if slot
        else ""
    )

    return QueueEntryResponse(
        queue_entry_id=next_entry.id,
        token_number=token.token_number if token else "",
        procurement_request_id=next_entry.procurement_request_id,
        dynamic_position=None,
        status=next_entry.status,
        is_late=next_entry.is_late,
        slot_window=slot_window,
        check_in_time=next_entry.check_in_time,
        called_at=next_entry.called_at,
        counter_or_bay=next_entry.counter_or_bay,
        vehicle_number=next_entry.vehicle_number,
    )


def update_queue_entry_status(
    db: Session,
    centre_id: UUID,
    queue_entry_id: UUID,
    update_data: QueueStatusUpdateRequest,
    now_override: Optional[datetime] = None,
) -> QueueEntryResponse:
    """Update queue entry status with strict state machine validation."""
    now_dt = now_override or datetime.now(timezone.utc)

    queue_entry = (
        db.query(QueueEntry)
        .filter(
            QueueEntry.id == queue_entry_id,
            QueueEntry.centre_id == centre_id,
        )
        .with_for_update()
        .first()
    )

    if queue_entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Queue entry not found",
        )

    target_status = update_data.status
    allowed_transitions = VALID_QUEUE_TRANSITIONS.get(queue_entry.status, set())

    if target_status not in allowed_transitions:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot transition queue entry from '{queue_entry.status}' "
                f"to '{target_status}'. Allowed transitions: {sorted(allowed_transitions)}"
            ),
        )

    # Perform status updates and timestamp recordings
    queue_entry.status = target_status
    if update_data.counter_or_bay:
        queue_entry.counter_or_bay = update_data.counter_or_bay

    if target_status == QueueStatus.PROCESSING.value:
        queue_entry.service_start_time = now_dt
    elif target_status == QueueStatus.COMPLETED.value:
        queue_entry.service_end_time = now_dt

    db.commit()
    db.refresh(queue_entry)

    token = db.query(Token).filter(Token.id == queue_entry.token_id).first()
    slot = db.query(CentreSlot).filter(CentreSlot.id == queue_entry.slot_id).first()
    slot_window = (
        f"{slot.start_time.strftime('%H:%M:%S')} - {slot.end_time.strftime('%H:%M:%S')}"
        if slot
        else ""
    )

    return QueueEntryResponse(
        queue_entry_id=queue_entry.id,
        token_number=token.token_number if token else "",
        procurement_request_id=queue_entry.procurement_request_id,
        dynamic_position=None,
        status=queue_entry.status,
        is_late=queue_entry.is_late,
        slot_window=slot_window,
        check_in_time=queue_entry.check_in_time,
        called_at=queue_entry.called_at,
        counter_or_bay=queue_entry.counter_or_bay,
        vehicle_number=queue_entry.vehicle_number,
    )
