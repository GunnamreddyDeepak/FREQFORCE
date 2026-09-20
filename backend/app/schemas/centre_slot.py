from datetime import date, time
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SlotResponse(BaseModel):
    """API schema for a single centre slot window."""

    model_config = ConfigDict(from_attributes=True)

    slot_id: UUID
    start_time: time
    end_time: time
    quantity_capacity: float
    booked_quantity: float
    remaining_quantity: float
    max_bookings: int
    booked_bookings: int
    remaining_bookings: int
    status: str


class CentreSlotsResponse(BaseModel):
    """API response for listing slots at a procurement centre on a specific date."""

    centre_id: UUID
    centre_name: str
    date: date
    daily_capacity_qtl: float
    daily_committed_qtl: float
    daily_remaining_qtl: float
    slots: list[SlotResponse] = Field(default_factory=list)
