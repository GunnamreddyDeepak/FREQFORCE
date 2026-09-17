from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProcurementRequestCreate(BaseModel):
    """API payload for creating a procurement request."""

    farmer_id: UUID
    commodity_id: UUID

    requested_quantity: float = Field(
        gt=0,
        description="Requested procurement quantity in quintals",
    )

    preferred_date: date

    latitude: float = Field(
        ge=-90,
        le=90,
        description="Farmer/request latitude in WGS84",
    )

    longitude: float = Field(
        ge=-180,
        le=180,
        description="Farmer/request longitude in WGS84",
    )


class ProcurementRequestResponse(BaseModel):
    """API response for a procurement request."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    farmer_id: UUID
    commodity_id: UUID
    requested_quantity: float
    preferred_date: date
    status: str