from uuid import UUID

from pydantic import BaseModel, Field


class EligibleCentreCandidate(BaseModel):
    """A procurement centre that can handle the procurement request."""

    centre_id: UUID
    centre_code: str
    centre_name: str
    available_capacity: float = Field(
        ge=0,
        description="Remaining daily procurement capacity in quintals",
    )
    reasons: list[str] = Field(
        default_factory=list,
        description="Deterministic reasons why the centre is eligible",
    )


class ProcurementEligibilityResponse(BaseModel):
    """Eligibility evaluation result for a procurement request."""

    procurement_request_id: UUID
    eligible_centres: list[EligibleCentreCandidate]
