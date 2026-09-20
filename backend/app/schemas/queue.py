from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CheckInRequest(BaseModel):
    """Payload for farmer gate check-in."""

    token_number: str
    vehicle_number: Optional[str] = None


class CheckInResponse(BaseModel):
    """Response returned upon successful physical gate check-in."""

    model_config = ConfigDict(from_attributes=True)

    queue_entry_id: UUID
    token_number: str
    procurement_request_id: UUID
    centre_id: UUID
    status: str
    is_late: bool
    slot_window: str
    check_in_time: datetime
    dynamic_position: int
    vehicle_number: Optional[str] = None


class QueueEntryResponse(BaseModel):
    """Single entry representation in the yard queue."""

    model_config = ConfigDict(from_attributes=True)

    queue_entry_id: UUID
    token_number: str
    procurement_request_id: UUID
    dynamic_position: Optional[int] = None
    status: str
    is_late: bool
    slot_window: str
    check_in_time: datetime
    called_at: Optional[datetime] = None
    counter_or_bay: Optional[str] = None
    vehicle_number: Optional[str] = None


class CentreQueueResponse(BaseModel):
    """Aggregated view of centre yard queue for a specific date."""

    centre_id: UUID
    queue_date: date
    total_waiting: int
    total_called: int
    total_processing: int
    entries: List[QueueEntryResponse]


class CallNextRequest(BaseModel):
    """Payload for desk/weighbridge operator calling next waiting farmer."""

    counter_or_bay: Optional[str] = None


class QueueStatusUpdateRequest(BaseModel):
    """Payload for operator advancing or updating queue entry status."""

    status: str
    counter_or_bay: Optional[str] = None
