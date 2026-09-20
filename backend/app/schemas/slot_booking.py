from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.schemas.token import TokenResponse


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
    token: Optional[TokenResponse] = None


class ProcurementRequestCancelResponse(BaseModel):
    """Response returned upon cancelling a confirmed procurement request."""

    procurement_request_id: UUID
    status: str
    message: str
