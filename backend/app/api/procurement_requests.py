from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.procurement_request import (
    ProcurementRequestCreate,
    ProcurementRequestResponse,
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