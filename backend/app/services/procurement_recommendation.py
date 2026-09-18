from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.centre_capacity import CentreCapacity
from app.models.procurement_centre import ProcurementCentre
from app.models.procurement_request import ProcurementRequest
from app.schemas.procurement_recommendation import (
    ProcurementRecommendationResponse,
    RecommendedCentre,
)
from app.services.procurement_eligibility import evaluate_eligible_centres


CAPACITY_WEIGHT = 0.60
DISTANCE_WEIGHT = 0.40


def get_centre_distances(
    db: Session,
    procurement_request: ProcurementRequest,
) -> list[tuple[ProcurementCentre, float]]:
    """Return active centres with distance from the farmer in kilometres."""

    distance_m = func.ST_DistanceSphere(
        procurement_request.farmer_location,
        ProcurementCentre.location,
    )

    rows = (
        db.query(
            ProcurementCentre,
            (distance_m / 1000.0).label("distance_km"),
        )
        .filter(ProcurementCentre.is_active.is_(True))
        .order_by(distance_m)
        .all()
    )

    return [
        (centre, float(distance_km))
        for centre, distance_km in rows
    ]


def calculate_projected_utilization(
    daily_capacity: float,
    committed_quantity: float,
    requested_quantity: float,
) -> float:
    """Calculate projected centre utilization after accepting a request."""

    if daily_capacity <= 0:
        raise ValueError("Daily capacity must be greater than zero")

    projected_quantity = committed_quantity + requested_quantity

    return projected_quantity / daily_capacity


def calculate_capacity_score(
    projected_utilization: float,
) -> float:
    """Convert projected utilization into a normalized capacity score."""

    if projected_utilization < 0:
        raise ValueError("Projected utilization cannot be negative")

    return max(
        0.0,
        min(1.0, 1.0 - projected_utilization),
    )


def calculate_distance_scores(
    distances_km: list[float],
) -> list[float]:
    """Normalize distances so the nearest centre scores highest."""

    if not distances_km:
        return []

    if any(distance < 0 for distance in distances_km):
        raise ValueError("Distance cannot be negative")

    nearest = min(distances_km)
    farthest = max(distances_km)

    if nearest == farthest:
        return [1.0] * len(distances_km)

    return [
        (farthest - distance) / (farthest - nearest)
        for distance in distances_km
    ]


def calculate_recommendation_score(
    capacity_score: float,
    distance_score: float,
) -> float:
    """Calculate the weighted recommendation score."""

    if not 0 <= capacity_score <= 1:
        raise ValueError("Capacity score must be between 0 and 1")

    if not 0 <= distance_score <= 1:
        raise ValueError("Distance score must be between 0 and 1")

    return (
        CAPACITY_WEIGHT * capacity_score
        + DISTANCE_WEIGHT * distance_score
    )


def rank_recommendation_candidates(
    candidates: list[dict],
) -> list[dict]:
    """Rank recommendation candidates by score.

    Ranking is deterministic:
    1. Higher recommendation score first.
    2. Centre code ascending for exact score ties.
    """

    ranked_candidates = []

    for candidate in candidates:
        capacity_score = candidate["capacity_score"]
        distance_score = candidate["distance_score"]

        recommendation_score = calculate_recommendation_score(
            capacity_score=capacity_score,
            distance_score=distance_score,
        )

        ranked_candidates.append(
            {
                **candidate,
                "score": recommendation_score,
            }
        )

    ranked_candidates.sort(
        key=lambda candidate: (
            -candidate["score"],
            candidate["centre_code"],
        )
    )

    return ranked_candidates


def recommend_procurement_centre(
    db: Session,
    procurement_request: ProcurementRequest,
) -> ProcurementRecommendationResponse:
    """Recommend and rank eligible procurement centres for a request.

    Eligibility determines which centres can accept the request.
    This function only ranks those eligible centres using capacity
    pressure and geographic distance.
    """

    eligibility = evaluate_eligible_centres(
        db=db,
        procurement_request=procurement_request,
    )

    if not eligibility.eligible_centres:
        return ProcurementRecommendationResponse(
            procurement_request_id=procurement_request.id,
            recommended_centre=None,
            alternative_centres=[],
        )

    distances = get_centre_distances(
        db=db,
        procurement_request=procurement_request,
    )

    distance_by_centre_id = {
        centre.id: distance_km
        for centre, distance_km in distances
    }

    eligible_centre_ids = [
        candidate.centre_id
        for candidate in eligibility.eligible_centres
    ]

    eligible_distance_centre_ids = [
        centre_id
        for centre_id in eligible_centre_ids
        if centre_id in distance_by_centre_id
    ]

    eligible_distances = [
        distance_by_centre_id[centre_id]
        for centre_id in eligible_distance_centre_ids
    ]

    distance_scores = calculate_distance_scores(
        eligible_distances
    )

    distance_score_by_centre_id = {
        centre_id: score
        for centre_id, score in zip(
            eligible_distance_centre_ids,
            distance_scores,
        )
    }

    capacity_rows = (
        db.query(CentreCapacity)
        .filter(
            CentreCapacity.centre_id.in_(eligible_centre_ids),
            CentreCapacity.capacity_date
            == procurement_request.preferred_date,
            CentreCapacity.is_active.is_(True),
        )
        .all()
    )

    capacity_by_centre_id = {
        capacity.centre_id: capacity
        for capacity in capacity_rows
    }

    candidates = []

    for eligible_centre in eligibility.eligible_centres:
        centre_id = eligible_centre.centre_id

        capacity = capacity_by_centre_id.get(centre_id)
        distance_km = distance_by_centre_id.get(centre_id)
        distance_score = distance_score_by_centre_id.get(centre_id)

        if (
            capacity is None
            or distance_km is None
            or distance_score is None
        ):
            continue

        projected_utilization = calculate_projected_utilization(
            daily_capacity=float(
                capacity.daily_quantity_capacity
            ),
            committed_quantity=float(
                capacity.committed_quantity
            ),
            requested_quantity=float(
                procurement_request.requested_quantity
            ),
        )

        capacity_score = calculate_capacity_score(
            projected_utilization
        )

        reasons = list(eligible_centre.reasons)

        if capacity_score > 0.50:
            reasons.append("LOWER_CAPACITY_PRESSURE")
        elif capacity_score > 0:
            reasons.append("AVAILABLE_CAPACITY_REMAINING")

        if distance_km == min(eligible_distances):
            reasons.append("NEAREST_ELIGIBLE_CENTRE")

        candidates.append(
            {
                "centre_id": centre_id,
                "centre_code": eligible_centre.centre_code,
                "centre_name": eligible_centre.centre_name,
                "distance_km": distance_km,
                "available_capacity": (
                    eligible_centre.available_capacity
                ),
                "capacity_score": capacity_score,
                "distance_score": distance_score,
                "reasons": reasons,
            }
        )

    ranked_candidates = rank_recommendation_candidates(
        candidates
    )

    if not ranked_candidates:
        return ProcurementRecommendationResponse(
            procurement_request_id=procurement_request.id,
            recommended_centre=None,
            alternative_centres=[],
        )

    recommended = ranked_candidates[0]

    recommended_centre = RecommendedCentre(
        centre_id=recommended["centre_id"],
        centre_code=recommended["centre_code"],
        centre_name=recommended["centre_name"],
        distance_km=recommended["distance_km"],
        available_capacity=recommended["available_capacity"],
        score=recommended["score"],
        reasons=recommended["reasons"],
    )

    alternative_centres = [
        RecommendedCentre(
            centre_id=candidate["centre_id"],
            centre_code=candidate["centre_code"],
            centre_name=candidate["centre_name"],
            distance_km=candidate["distance_km"],
            available_capacity=candidate["available_capacity"],
            score=candidate["score"],
            reasons=candidate["reasons"],
        )
        for candidate in ranked_candidates[1:]
    ]

    return ProcurementRecommendationResponse(
        procurement_request_id=procurement_request.id,
        recommended_centre=recommended_centre,
        alternative_centres=alternative_centres,
    )