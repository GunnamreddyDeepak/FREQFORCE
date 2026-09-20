from datetime import date, time
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.centre_capacity import CentreCapacity
from app.models.centre_slot import CentreSlot, SlotStatus
from app.models.procurement_centre import ProcurementCentre
from app.schemas.centre_slot import CentreSlotsResponse, SlotResponse


# Standard fixed non-overlapping 2-hour windows for MVP
STANDARD_SLOT_WINDOWS = [
    (time(9, 0, 0), time(11, 0, 0)),
    (time(11, 0, 0), time(13, 0, 0)),
    (time(13, 0, 0), time(15, 0, 0)),
    (time(15, 0, 0), time(17, 0, 0)),
]


def generate_daily_slots(
    db: Session,
    centre_id: UUID,
    slot_date: date,
    daily_capacity: Decimal | float | None = None,
) -> list[CentreSlot]:
    """Deterministically generate fixed 2-hour slots for a centre on a specific date.

    Idempotent: Running multiple times does not duplicate existing slots.
    """
    centre = (
        db.query(ProcurementCentre)
        .filter(ProcurementCentre.id == centre_id)
        .first()
    )
    if centre is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procurement centre not found",
        )

    capacity = (
        db.query(CentreCapacity)
        .filter(
            CentreCapacity.centre_id == centre_id,
            CentreCapacity.capacity_date == slot_date,
        )
        .first()
    )
    if capacity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Centre capacity not configured for date {slot_date}",
        )

    total_capacity = (
        Decimal(str(daily_capacity))
        if daily_capacity is not None
        else Decimal(str(capacity.daily_quantity_capacity))
    )

    slot_quantity_capacity = (total_capacity / Decimal("4")).quantize(
        Decimal("0.001")
    )

    existing_slots = (
        db.query(CentreSlot)
        .filter(
            CentreSlot.centre_id == centre_id,
            CentreSlot.slot_date == slot_date,
        )
        .all()
    )

    existing_window_map = {
        (s.start_time, s.end_time): s for s in existing_slots
    }

    created_or_existing_slots: list[CentreSlot] = []

    for start_t, end_t in STANDARD_SLOT_WINDOWS:
        if (start_t, end_t) in existing_window_map:
            created_or_existing_slots.append(existing_window_map[(start_t, end_t)])
        else:
            new_slot = CentreSlot(
                centre_id=centre_id,
                capacity_id=capacity.id,
                slot_date=slot_date,
                start_time=start_t,
                end_time=end_t,
                quantity_capacity=slot_quantity_capacity,
                booked_quantity=Decimal("0.000"),
                max_bookings=20,
                booked_bookings=0,
                status=SlotStatus.AVAILABLE.value,
            )
            db.add(new_slot)
            created_or_existing_slots.append(new_slot)

    db.flush()
    return created_or_existing_slots


def get_centre_slots(
    db: Session,
    centre_id: UUID,
    slot_date: date,
) -> CentreSlotsResponse:
    """Return all slot windows and available capacities for a centre on a given date."""
    centre = (
        db.query(ProcurementCentre)
        .filter(ProcurementCentre.id == centre_id)
        .first()
    )
    if centre is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procurement centre not found",
        )

    capacity = (
        db.query(CentreCapacity)
        .filter(
            CentreCapacity.centre_id == centre_id,
            CentreCapacity.capacity_date == slot_date,
        )
        .first()
    )
    if capacity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No capacity configured for centre on date {slot_date}",
        )

    # Ensure standard slots are populated
    generate_daily_slots(
        db=db,
        centre_id=centre_id,
        slot_date=slot_date,
        daily_capacity=Decimal(str(capacity.daily_quantity_capacity)),
    )
    db.commit()

    slots = (
        db.query(CentreSlot)
        .filter(
            CentreSlot.centre_id == centre_id,
            CentreSlot.slot_date == slot_date,
        )
        .order_by(CentreSlot.start_time)
        .all()
    )

    daily_capacity_val = float(capacity.daily_quantity_capacity)
    daily_committed_val = float(capacity.committed_quantity)
    daily_remaining_val = max(0.0, daily_capacity_val - daily_committed_val)

    slot_responses = [
        SlotResponse(
            slot_id=s.id,
            start_time=s.start_time,
            end_time=s.end_time,
            quantity_capacity=float(s.quantity_capacity),
            booked_quantity=float(s.booked_quantity),
            remaining_quantity=float(s.remaining_quantity),
            max_bookings=s.max_bookings,
            booked_bookings=s.booked_bookings,
            remaining_bookings=s.remaining_bookings,
            status=s.status,
        )
        for s in slots
    ]

    return CentreSlotsResponse(
        centre_id=centre.id,
        centre_name=centre.name,
        date=slot_date,
        daily_capacity_qtl=daily_capacity_val,
        daily_committed_qtl=daily_committed_val,
        daily_remaining_qtl=daily_remaining_val,
        slots=slot_responses,
    )
