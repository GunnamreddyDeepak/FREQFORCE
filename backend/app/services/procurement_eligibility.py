from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.centre_capacity import CentreCapacity
from app.models.centre_commodity import CentreCommodity
from app.models.commodity import Commodity
from app.models.procurement_centre import ProcurementCentre
from app.models.procurement_request import ProcurementRequest
from app.schemas.procurement_eligibility import (
    EligibleCentreCandidate,
    ProcurementEligibilityResponse,
)


def evaluate_eligible_centres(
    db: Session,
    procurement_request: ProcurementRequest,
) -> ProcurementEligibilityResponse:
    """Evaluate which procurement centres can handle a request.

    Eligibility is deterministic and based on:
    - active centre
    - active commodity
    - active commodity capability
    - active capacity configuration for the requested date
    - sufficient remaining capacity

    This service does not rank or recommend centres.
    """

    if procurement_request.status != "REQUESTED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Procurement request is not in REQUESTED status",
        )

    commodity = (
        db.query(Commodity)
        .filter(
            Commodity.id == procurement_request.commodity_id,
            Commodity.is_active.is_(True),
        )
        .first()
    )

    if commodity is None:
        return ProcurementEligibilityResponse(
            procurement_request_id=procurement_request.id,
            eligible_centres=[],
        )

    centres = (
        db.query(ProcurementCentre)
        .filter(ProcurementCentre.is_active.is_(True))
        .order_by(ProcurementCentre.centre_code)
        .all()
    )

    eligible_centres: list[EligibleCentreCandidate] = []

    for centre in centres:
        capability = (
            db.query(CentreCommodity)
            .filter(
                CentreCommodity.centre_id == centre.id,
                CentreCommodity.commodity_id == procurement_request.commodity_id,
                CentreCommodity.is_active.is_(True),
            )
            .first()
        )

        if capability is None:
            continue

        capacity = (
            db.query(CentreCapacity)
            .filter(
                CentreCapacity.centre_id == centre.id,
                CentreCapacity.capacity_date == procurement_request.preferred_date,
                CentreCapacity.is_active.is_(True),
            )
            .first()
        )

        if capacity is None:
            continue

        available_capacity = float(
            capacity.daily_quantity_capacity - capacity.committed_quantity
        )

        if available_capacity < procurement_request.requested_quantity:
            continue

        eligible_centres.append(
            EligibleCentreCandidate(
                centre_id=centre.id,
                centre_code=centre.centre_code,
                centre_name=centre.name,
                available_capacity=available_capacity,
                reasons=[
                    "CENTRE_ACTIVE",
                    "COMMODITY_SUPPORTED",
                    "CAPACITY_AVAILABLE",
                ],
            )
        )

    return ProcurementEligibilityResponse(
        procurement_request_id=procurement_request.id,
        eligible_centres=eligible_centres,
    )
