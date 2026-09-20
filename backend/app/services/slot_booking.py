from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.centre_capacity import CentreCapacity
from app.models.centre_slot import CentreSlot, SlotStatus
from app.models.procurement_centre import ProcurementCentre
from app.models.procurement_request import (
    ProcurementRequest,
    ProcurementRequestStatus,
)
from app.models.queue_entry import QueueEntry, QueueStatus
from app.models.token import Token, TokenStatus
from app.schemas.slot_booking import (
    ProcurementRequestCancelResponse,
    SlotConfirmResponse,
)
from app.schemas.token import TokenResponse
from app.services.procurement_eligibility import evaluate_eligible_centres
from app.services.procurement_request_state import (
    transition_procurement_request,
)
from app.services.token import allocate_token


def confirm_procurement_slot(
    db: Session,
    request_id: UUID,
    centre_id: UUID,
    slot_id: UUID,
) -> SlotConfirmResponse:
    """Atomically confirm an operational slot and issue an arrival token for a procurement request.

    Enforces strict canonical lock order (partial ascending order):
    1. ProcurementRequest (FOR UPDATE)
    2. CentreSlot (FOR UPDATE)
    3. CentreCapacity (FOR UPDATE)
    4. TokenSequence (FOR UPDATE via allocate_token)

    Validates eligibility, dual-level capacity bounds, and FSM transitions atomically:
    REQUESTED -> ELIGIBILITY_CHECKED -> CENTRE_RECOMMENDED -> SLOT_CONFIRMED -> TOKEN_GENERATED.
    """
    # 1. Lock ProcurementRequest
    procurement_request = (
        db.query(ProcurementRequest)
        .filter(ProcurementRequest.id == request_id)
        .with_for_update()
        .first()
    )
    if procurement_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procurement request not found",
        )

    # 2. Idempotency & Conflict Checks on Request
    if procurement_request.status in (
        ProcurementRequestStatus.SLOT_CONFIRMED.value,
        ProcurementRequestStatus.TOKEN_GENERATED.value,
    ):
        if (
            procurement_request.confirmed_slot_id == slot_id
            and procurement_request.confirmed_centre_id == centre_id
        ):
            # Idempotent replay: return existing confirmation and token
            slot = (
                db.query(CentreSlot)
                .filter(CentreSlot.id == slot_id)
                .first()
            )
            centre = (
                db.query(ProcurementCentre)
                .filter(ProcurementCentre.id == centre_id)
                .first()
            )
            token = (
                db.query(Token)
                .filter(Token.procurement_request_id == procurement_request.id)
                .first()
            )
            centre_name = centre.name if centre else "Procurement Centre"
            slot_window = (
                f"{slot.start_time.strftime('%H:%M:%S')} - {slot.end_time.strftime('%H:%M:%S')}"
                if slot
                else ""
            )
            token_response = TokenResponse.model_validate(token) if token else None
            return SlotConfirmResponse(
                procurement_request_id=procurement_request.id,
                centre_id=centre_id,
                centre_name=centre_name,
                slot_id=slot_id,
                slot_date=procurement_request.preferred_date,
                slot_window=slot_window,
                booked_quantity=float(procurement_request.requested_quantity),
                status=procurement_request.status,
                token=token_response,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Procurement request is already confirmed for another slot",
            )

    if procurement_request.status not in (
        ProcurementRequestStatus.REQUESTED.value,
        ProcurementRequestStatus.ELIGIBILITY_CHECKED.value,
        ProcurementRequestStatus.CENTRE_RECOMMENDED.value,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot confirm slot for request in status '{procurement_request.status}'",
        )

    # 3. Lock CentreSlot
    slot = (
        db.query(CentreSlot)
        .filter(CentreSlot.id == slot_id)
        .with_for_update()
        .first()
    )
    if slot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Centre slot not found",
        )

    if slot.centre_id != centre_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Slot does not belong to the specified procurement centre",
        )

    if slot.slot_date != procurement_request.preferred_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Slot date does not match the procurement request preferred date",
        )

    if slot.status != SlotStatus.AVAILABLE.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Slot is not available for booking (status: {slot.status})",
        )

    # 4. Lock CentreCapacity
    capacity = (
        db.query(CentreCapacity)
        .filter(CentreCapacity.id == slot.capacity_id)
        .with_for_update()
        .first()
    )
    if capacity is None or not capacity.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Centre capacity configuration is inactive or not found",
        )

    centre = (
        db.query(ProcurementCentre)
        .filter(ProcurementCentre.id == centre_id)
        .first()
    )
    if centre is None or not centre.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Procurement centre is inactive or not found",
        )

    # 5. Re-run Eligibility Engine against current state
    eligibility = evaluate_eligible_centres(
        db=db,
        procurement_request=procurement_request,
    )
    eligible_centre_ids = [c.centre_id for c in eligibility.eligible_centres]
    if centre_id not in eligible_centre_ids:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Target procurement centre is not currently eligible for this request",
        )

    # 6. Step 1 State Transition: REQUESTED -> ELIGIBILITY_CHECKED
    if procurement_request.status == ProcurementRequestStatus.REQUESTED.value:
        transition_procurement_request(
            procurement_request=procurement_request,
            target_status=ProcurementRequestStatus.ELIGIBILITY_CHECKED,
            db=db,
        )

    # 7. Step 2 State Transition: ELIGIBILITY_CHECKED -> CENTRE_RECOMMENDED
    if procurement_request.status == ProcurementRequestStatus.ELIGIBILITY_CHECKED.value:
        transition_procurement_request(
            procurement_request=procurement_request,
            target_status=ProcurementRequestStatus.CENTRE_RECOMMENDED,
            db=db,
        )

    # 8. Capacity Invariant Validation using Decimal Arithmetic
    req_qty = Decimal(str(procurement_request.requested_quantity))
    slot_remaining_qty = slot.quantity_capacity - slot.booked_quantity
    slot_remaining_bookings = slot.max_bookings - slot.booked_bookings
    daily_remaining_qty = capacity.daily_quantity_capacity - capacity.committed_quantity

    if req_qty > slot_remaining_qty:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Requested quantity ({req_qty} qtl) exceeds remaining slot capacity ({slot_remaining_qty} qtl)",
        )

    if slot_remaining_bookings < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Slot has reached maximum booking count",
        )

    if req_qty > daily_remaining_qty:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Requested quantity ({req_qty} qtl) exceeds remaining daily centre capacity ({daily_remaining_qty} qtl)",
        )

    # 9. Atomic Capacity & Booking Count Updates
    slot.booked_quantity = slot.booked_quantity + req_qty
    slot.booked_bookings = slot.booked_bookings + 1
    if (
        slot.booked_quantity >= slot.quantity_capacity
        or slot.booked_bookings >= slot.max_bookings
    ):
        slot.status = SlotStatus.FULL.value

    capacity.committed_quantity = capacity.committed_quantity + req_qty

    # 10. Step 3 State Transition: CENTRE_RECOMMENDED -> SLOT_CONFIRMED
    procurement_request.confirmed_centre_id = centre_id
    procurement_request.confirmed_slot_id = slot_id

    transition_procurement_request(
        procurement_request=procurement_request,
        target_status=ProcurementRequestStatus.SLOT_CONFIRMED,
        db=db,
    )

    # 11. Step 4 State Transition & Token Issuance: SLOT_CONFIRMED -> TOKEN_GENERATED
    transition_procurement_request(
        procurement_request=procurement_request,
        target_status=ProcurementRequestStatus.TOKEN_GENERATED,
        db=db,
    )

    # 12. Allocate Monotonic Sequence & Insert Token
    token = allocate_token(
        db=db,
        centre=centre,
        slot=slot,
        procurement_request=procurement_request,
    )

    db.commit()
    db.refresh(procurement_request)
    db.refresh(slot)
    db.refresh(token)

    slot_window = (
        f"{slot.start_time.strftime('%H:%M:%S')} - {slot.end_time.strftime('%H:%M:%S')}"
    )

    return SlotConfirmResponse(
        procurement_request_id=procurement_request.id,
        centre_id=centre.id,
        centre_name=centre.name,
        slot_id=slot.id,
        slot_date=slot.slot_date,
        slot_window=slot_window,
        booked_quantity=float(procurement_request.requested_quantity),
        status=procurement_request.status,
        token=TokenResponse.model_validate(token),
    )


def cancel_procurement_request(
    db: Session,
    request_id: UUID,
) -> ProcurementRequestCancelResponse:
    """Atomically cancel a procurement request and release reserved capacity and token.

    Enforces ascending partial lock order:
    1. ProcurementRequest (FOR UPDATE)
    2. CentreSlot (FOR UPDATE)
    3. CentreCapacity (FOR UPDATE)
    4. Token (FOR UPDATE)
    5. QueueEntry (FOR UPDATE)
    """
    # 1. Lock ProcurementRequest
    procurement_request = (
        db.query(ProcurementRequest)
        .filter(ProcurementRequest.id == request_id)
        .with_for_update()
        .first()
    )
    if procurement_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procurement request not found",
        )

    if procurement_request.status == ProcurementRequestStatus.CANCELLED.value:
        return ProcurementRequestCancelResponse(
            procurement_request_id=procurement_request.id,
            status=procurement_request.status,
            message="Procurement request is already cancelled",
        )

    if procurement_request.status not in (
        ProcurementRequestStatus.REQUESTED.value,
        ProcurementRequestStatus.ELIGIBILITY_CHECKED.value,
        ProcurementRequestStatus.CENTRE_RECOMMENDED.value,
        ProcurementRequestStatus.SLOT_CONFIRMED.value,
        ProcurementRequestStatus.TOKEN_GENERATED.value,
        ProcurementRequestStatus.CHECKED_IN.value,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel procurement request in status '{procurement_request.status}'",
        )

    # 2. Lock CentreSlot & 3. Lock CentreCapacity if slot confirmed
    slot = None
    if procurement_request.confirmed_slot_id is not None:
        slot = (
            db.query(CentreSlot)
            .filter(CentreSlot.id == procurement_request.confirmed_slot_id)
            .with_for_update()
            .first()
        )
        if slot is not None:
            capacity = (
                db.query(CentreCapacity)
                .filter(CentreCapacity.id == slot.capacity_id)
                .with_for_update()
                .first()
            )

            req_qty = Decimal(str(procurement_request.requested_quantity))
            slot.booked_quantity = max(Decimal("0.000"), slot.booked_quantity - req_qty)
            slot.booked_bookings = max(0, slot.booked_bookings - 1)

            if (
                slot.status == SlotStatus.FULL.value
                and slot.booked_quantity < slot.quantity_capacity
                and slot.booked_bookings < slot.max_bookings
            ):
                slot.status = SlotStatus.AVAILABLE.value

            if capacity is not None:
                capacity.committed_quantity = max(
                    Decimal("0.000"), capacity.committed_quantity - req_qty
                )

    # 4. Lock Token & update status if present
    token = (
        db.query(Token)
        .filter(Token.procurement_request_id == procurement_request.id)
        .with_for_update()
        .first()
    )
    if token is not None:
        token.status = TokenStatus.CANCELLED.value

    # 5. Lock QueueEntry & update status if present
    queue_entry = (
        db.query(QueueEntry)
        .filter(QueueEntry.procurement_request_id == procurement_request.id)
        .with_for_update()
        .first()
    )
    if queue_entry is not None:
        if queue_entry.status in (QueueStatus.PROCESSING.value, QueueStatus.COMPLETED.value):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot cancel request in queue status '{queue_entry.status}'",
            )
        queue_entry.status = QueueStatus.CANCELLED.value

    # Transition ProcurementRequest to CANCELLED
    transition_procurement_request(
        procurement_request=procurement_request,
        target_status=ProcurementRequestStatus.CANCELLED,
        db=db,
    )

    db.commit()

    return ProcurementRequestCancelResponse(
        procurement_request_id=procurement_request.id,
        status=procurement_request.status,
        message="Procurement request successfully cancelled and capacity released",
    )
