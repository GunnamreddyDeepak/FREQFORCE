from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.procurement_request import ProcurementRequest
from app.schemas.procurement_eligibility import ProcurementEligibilityResponse
from app.schemas.procurement_recommendation import (
    ProcurementRecommendationResponse,
)
from app.schemas.procurement_request import (
    ProcurementRequestCreate,
    ProcurementRequestResponse,
)
from app.services.procurement_eligibility import evaluate_eligible_centres
from app.services.procurement_recommendation import (
    recommend_procurement_centre,
)
from app.services.procurement_request import create_procurement_request

router = APIRouter(
    prefix="/api/v1/procurement-requests",
    tags=["Procurement Requests"],
)


@router.post(
    "",
    response_model=ProcurementRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a procurement request",
)
def create_request(
    request_data: ProcurementRequestCreate,
    db: Session = Depends(get_db),
) -> ProcurementRequestResponse:
    """Create a new farmer procurement request."""

    procurement_request = create_procurement_request(
        db=db,
        request_data=request_data,
    )

    return ProcurementRequestResponse.model_validate(
        procurement_request
    )


@router.get(
    "/{request_id}/eligibility",
    response_model=ProcurementEligibilityResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate eligible procurement centres",
)
def evaluate_request_eligibility(
    request_id: UUID,
    db: Session = Depends(get_db),
) -> ProcurementEligibilityResponse:
    """Evaluate which active centres can handle a procurement request."""

    procurement_request = (
        db.query(ProcurementRequest)
        .filter(ProcurementRequest.id == request_id)
        .first()
    )

    if procurement_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procurement request not found",
        )

    return evaluate_eligible_centres(
        db=db,
        procurement_request=procurement_request,
    )


@router.post(
    "/{request_id}/recommendations",
    response_model=ProcurementRecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get centre recommendations for a procurement request",
)
def get_recommendations(
    request_id: UUID,
    db: Session = Depends(get_db),
) -> ProcurementRecommendationResponse:
    """Recommend and rank eligible procurement centres for a request."""

    procurement_request = (
        db.query(ProcurementRequest)
        .filter(ProcurementRequest.id == request_id)
        .first()
    )

    if procurement_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procurement request not found",
        )

    return recommend_procurement_centre(
        db=db,
        procurement_request=procurement_request,
    )