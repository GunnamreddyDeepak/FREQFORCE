import pytest
from geoalchemy2 import WKTElement

from app.db.session import get_session_factory
from app.models.procurement_centre import ProcurementCentre
from app.models.procurement_request import ProcurementRequest
from app.services.procurement_recommendation import (
    calculate_capacity_score,
    calculate_distance_scores,
    calculate_projected_utilization,
    calculate_recommendation_score,
    get_centre_distances,
    rank_recommendation_candidates,
    recommend_procurement_centre,
)


def test_get_centre_distances_returns_distance(
    eligibility_test_data,
):
    data = eligibility_test_data

    SessionLocal = get_session_factory()
    db = SessionLocal()

    try:
        procurement_request = (
            db.query(ProcurementRequest)
            .filter(
                ProcurementRequest.id == data["request_id"],
            )
            .first()
        )

        assert procurement_request is not None

        rows = get_centre_distances(
            db=db,
            procurement_request=procurement_request,
        )

        assert len(rows) >= 1

        matching = [r for r in rows if r[0].id == data["centre_id"]]
        assert len(matching) == 1
        centre, distance_km = matching[0]

        assert centre.id == data["centre_id"]
        assert distance_km < 0.001
    finally:
        db.close()


def test_get_centre_distances_calculates_nonzero_distance(
    eligibility_test_data,
):
    data = eligibility_test_data

    SessionLocal = get_session_factory()
    db = SessionLocal()

    try:
        procurement_request = (
            db.query(ProcurementRequest)
            .filter(
                ProcurementRequest.id == data["request_id"],
            )
            .first()
        )

        centre = (
            db.query(ProcurementCentre)
            .filter(
                ProcurementCentre.id == data["centre_id"],
            )
            .first()
        )

        assert procurement_request is not None
        assert centre is not None

        procurement_request.farmer_location = WKTElement(
            "POINT(80.2800 13.0900)",
            srid=4326,
        )

        db.commit()
        db.refresh(procurement_request)

        rows = get_centre_distances(
            db=db,
            procurement_request=procurement_request,
        )

        assert len(rows) >= 1

        matching = [r for r in rows if r[0].id == centre.id]
        assert len(matching) == 1
        returned_centre, distance_km = matching[0]

        assert returned_centre.id == centre.id
        assert distance_km > 0
        assert distance_km < 2
    finally:
        db.close()


def test_calculate_projected_utilization():
    utilization = calculate_projected_utilization(
        daily_capacity=1000,
        committed_quantity=300,
        requested_quantity=70,
    )

    assert utilization == pytest.approx(0.37)


def test_calculate_projected_utilization_can_exceed_capacity():
    utilization = calculate_projected_utilization(
        daily_capacity=1000,
        committed_quantity=950,
        requested_quantity=100,
    )

    assert utilization == pytest.approx(1.05)


def test_calculate_projected_utilization_rejects_zero_capacity():
    with pytest.raises(ValueError, match="Daily capacity"):
        calculate_projected_utilization(
            daily_capacity=0,
            committed_quantity=100,
            requested_quantity=50,
        )


def test_calculate_capacity_score():
    score = calculate_capacity_score(0.30)

    assert score == pytest.approx(0.70)


def test_calculate_capacity_score_returns_zero_when_overloaded():
    score = calculate_capacity_score(1.10)

    assert score == 0.0


def test_calculate_capacity_score_rejects_negative_utilization():
    with pytest.raises(ValueError, match="cannot be negative"):
        calculate_capacity_score(-0.10)


def test_calculate_distance_scores():
    scores = calculate_distance_scores([2.0, 5.0, 10.0])

    assert scores[0] == pytest.approx(1.0)
    assert scores[1] == pytest.approx(0.625)
    assert scores[2] == pytest.approx(0.0)


def test_calculate_distance_scores_same_distance():
    scores = calculate_distance_scores([5.0, 5.0, 5.0])

    assert scores == [1.0, 1.0, 1.0]


def test_calculate_distance_scores_rejects_negative_distance():
    with pytest.raises(ValueError, match="Distance"):
        calculate_distance_scores([2.0, -1.0])


def test_calculate_distance_scores_empty_list():
    assert calculate_distance_scores([]) == []


def test_calculate_recommendation_score():
    score = calculate_recommendation_score(
        capacity_score=0.70,
        distance_score=1.0,
    )

    assert score == pytest.approx(0.82)


def test_calculate_recommendation_score_rejects_invalid_capacity_score():
    with pytest.raises(ValueError, match="Capacity score"):
        calculate_recommendation_score(
            capacity_score=1.10,
            distance_score=0.50,
        )


def test_calculate_recommendation_score_rejects_invalid_distance_score():
    with pytest.raises(ValueError, match="Distance score"):
        calculate_recommendation_score(
            capacity_score=0.50,
            distance_score=-0.10,
        )


def test_rank_recommendation_candidates():
    candidates = [
        {
            "centre_code": "C003",
            "capacity_score": 0.50,
            "distance_score": 0.50,
        },
        {
            "centre_code": "C001",
            "capacity_score": 0.80,
            "distance_score": 1.00,
        },
        {
            "centre_code": "C002",
            "capacity_score": 0.60,
            "distance_score": 0.80,
        },
    ]

    ranked = rank_recommendation_candidates(candidates)

    assert [candidate["centre_code"] for candidate in ranked] == [
        "C001",
        "C002",
        "C003",
    ]

    assert ranked[0]["score"] == pytest.approx(0.88)


def test_rank_recommendation_candidates_uses_centre_code_for_ties():
    candidates = [
        {
            "centre_code": "C002",
            "capacity_score": 0.70,
            "distance_score": 0.80,
        },
        {
            "centre_code": "C001",
            "capacity_score": 0.70,
            "distance_score": 0.80,
        },
    ]

    ranked = rank_recommendation_candidates(candidates)

    assert [candidate["centre_code"] for candidate in ranked] == [
        "C001",
        "C002",
    ]


def test_rank_recommendation_candidates_preserves_candidate_data():
    candidates = [
        {
            "centre_code": "C001",
            "capacity_score": 0.70,
            "distance_score": 1.00,
            "available_capacity": 500.0,
        },
    ]

    ranked = rank_recommendation_candidates(candidates)

    assert ranked[0]["centre_code"] == "C001"
    assert ranked[0]["available_capacity"] == 500.0
    assert "score" in ranked[0]


def test_recommend_procurement_centre_returns_recommendation(
    eligibility_test_data,
):
    data = eligibility_test_data

    SessionLocal = get_session_factory()
    db = SessionLocal()

    try:
        procurement_request = (
            db.query(ProcurementRequest)
            .filter(
                ProcurementRequest.id == data["request_id"],
            )
            .first()
        )

        assert procurement_request is not None

        result = recommend_procurement_centre(
            db=db,
            procurement_request=procurement_request,
        )

        assert result.procurement_request_id == procurement_request.id

        assert result.recommended_centre is not None

        recommended = result.recommended_centre

        assert recommended.centre_id == data["centre_id"]
        assert recommended.distance_km < 0.001
        assert recommended.available_capacity == pytest.approx(80.0)
        assert recommended.score == pytest.approx(0.46)

        assert "CENTRE_ACTIVE" in recommended.reasons
        assert "COMMODITY_SUPPORTED" in recommended.reasons
        assert "CAPACITY_AVAILABLE" in recommended.reasons
        assert "AVAILABLE_CAPACITY_REMAINING" in recommended.reasons
        assert "NEAREST_ELIGIBLE_CENTRE" in recommended.reasons

        assert result.alternative_centres == []
    finally:
        db.close()