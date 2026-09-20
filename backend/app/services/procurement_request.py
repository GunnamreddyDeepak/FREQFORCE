from uuid import UUID

from fastapi import HTTPException, status
from geoalchemy2 import WKTElement
from sqlalchemy.orm import Session

from app.models.commodity import Commodity
from app.models.farmer import Farmer
from app.models.procurement_request import (
    ProcurementRequest,
    ProcurementRequestStatus,
)
from app.schemas.procurement_request import ProcurementRequestCreate


def create_procurement_request(
    db: Session,
    request_data: ProcurementRequestCreate,
) -> ProcurementRequest:
    """Create a new farmer procurement request."""

    farmer = (
        db.query(Farmer)
        .filter(
            Farmer.id == request_data.farmer_id,
            Farmer.is_active.is_(True),
        )
        .first()
    )

    if farmer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active farmer not found",
        )

    commodity = (
        db.query(Commodity)
        .filter(
            Commodity.id == request_data.commodity_id,
            Commodity.is_active.is_(True),
        )
        .first()
    )

    if commodity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active commodity not found",
        )

    location = WKTElement(
        f"POINT({request_data.longitude} {request_data.latitude})",
        srid=4326,
    )

    procurement_request = ProcurementRequest(
        farmer_id=request_data.farmer_id,
        commodity_id=request_data.commodity_id,
        requested_quantity=request_data.requested_quantity,
        preferred_date=request_data.preferred_date,
        farmer_location=location,
        status=ProcurementRequestStatus.REQUESTED.value,
    )

    db.add(procurement_request)
    db.commit()
    db.refresh(procurement_request)

    return procurement_request