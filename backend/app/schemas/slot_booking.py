from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


class SlotConfirmRequest(BaseModel):
    """Payload for confirming an operational slot for a procurement request."""

    centre_id: UUID
    slot_id: UUID


class SlotConfirmResponse(BaseModel):
    """Response returned upon successful slot confirmation."""

    procurement_request_id: UUID
    centre_id: UUID
    centre_name: str
    slot_id: UUID
    slot_date: date
    slot_window: str
    booked_quantity: float
    status: str


class ProcurementRequestCancelResponse(BaseModel):
    """Response returned upon cancelling a confirmed procurement request."""

    procurement_request_id: UUID
    status: str
    message: str
