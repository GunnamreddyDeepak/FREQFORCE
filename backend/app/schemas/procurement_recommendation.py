from uuid import UUID

from pydantic import BaseModel, Field


class RecommendedCentre(BaseModel):
    """A procurement centre recommended for the request."""

    centre_id: UUID
    centre_code: str
    centre_name: str
    distance_km: float = Field(
        ge=0,
        description="Distance from farmer to procurement centre in kilometres",
    )
    available_capacity: float = Field(
        ge=0,
        description="Remaining daily procurement capacity in quintals",
    )
    score: float = Field(
        ge=0,
        le=1,
        description="Normalized recommendation score",
    )
    reasons: list[str] = Field(
        default_factory=list,
        description="Explainable reasons supporting the recommendation",
    )


class ProcurementRecommendationResponse(BaseModel):
    """Recommendation result for a procurement request."""

    procurement_request_id: UUID
    recommended_centre: RecommendedCentre | None = None
    alternative_centres: list[RecommendedCentre] = Field(
        default_factory=list,
    )
