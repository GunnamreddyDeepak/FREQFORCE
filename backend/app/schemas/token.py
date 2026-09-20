from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TokenResponse(BaseModel):
    """Schema representing an issued arrival token."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    token_number: str
    procurement_request_id: UUID
    centre_id: UUID
    slot_id: UUID
    token_date: date
    status: str
    created_at: datetime
