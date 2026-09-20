import uuid

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_session_factory
from app.main import app
from app.models.procurement_centre import ProcurementCentre
from app.models.procurement_request import ProcurementRequest
from app.services.procurement_recommendation import recommend_procurement_centre

client = TestClient(app)


def test_recommendations_endpoint_success(eligibility_test_data):
    """Verifies successful recommendation via the HTTP endpoint."""
    request_id = eligibility_test_data["request_id"]
    centre_id = eligibility_test_data["centre_id"]

    response = client.post(
        f"/api/v1/procurement-requests/{request_id}/recommendations"
    )

    assert response.status_code == 200
    data = response.json()

    assert data["procurement_request_id"] == str(request_id)
    assert data["recommended_centre"] is not None

    recommended = data["recommended_centre"]
    assert recommended["centre_id"] == str(centre_id)
    assert recommended["centre_code"].startswith("ELIG-")
    assert recommended["centre_name"] == "Eligibility Test Centre"
    assert recommended["distance_km"] < 0.001
    assert recommended["available_capacity"] == pytest.approx(80.0)
    assert recommended["score"] == pytest.approx(0.46)

    assert "CENTRE_ACTIVE" in recommended["reasons"]
    assert "COMMODITY_SUPPORTED" in recommended["reasons"]
    assert "CAPACITY_AVAILABLE" in recommended["reasons"]
    assert "AVAILABLE_CAPACITY_REMAINING" in recommended["reasons"]
    assert "NEAREST_ELIGIBLE_CENTRE" in recommended["reasons"]

    assert data["alternative_centres"] == []


def test_recommendations_endpoint_request_not_found():
    """Verifies that an unknown procurement request returns HTTP 404."""
    unknown_id = uuid.uuid4()
    response = client.post(
        f"/api/v1/procurement-requests/{unknown_id}/recommendations"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Procurement request not found"


def test_recommendations_endpoint_no_eligible_centres(eligibility_test_data):
    """Verifies recommendation response when no centres are eligible."""
    factory = get_session_factory()
    db = factory()

    try:
        centre = (
            db.query(ProcurementCentre)
            .filter(ProcurementCentre.id == eligibility_test_data["centre_id"])
            .one()
        )
        centre.is_active = False
        db.commit()

        response = client.post(
            f"/api/v1/procurement-requests/{eligibility_test_data['request_id']}/recommendations"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["procurement_request_id"] == str(
            eligibility_test_data["request_id"]
        )
        assert data["recommended_centre"] is None
        assert data["alternative_centres"] == []

    finally:
        db.close()


def test_recommendations_endpoint_deterministic_response(eligibility_test_data):
    """Verifies that multiple calls return identical recommendation results."""
    request_id = eligibility_test_data["request_id"]

    response1 = client.post(
        f"/api/v1/procurement-requests/{request_id}/recommendations"
    )
    response2 = client.post(
        f"/api/v1/procurement-requests/{request_id}/recommendations"
    )

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1.json() == response2.json()


def test_existing_service_behaviour_remains_unchanged(eligibility_test_data):
    """Verifies that the endpoint response matches the service output directly."""
    factory = get_session_factory()
    db = factory()

    try:
        procurement_request = (
            db.query(ProcurementRequest)
            .filter(
                ProcurementRequest.id == eligibility_test_data["request_id"]
            )
            .one()
        )

        service_result = recommend_procurement_centre(
            db=db,
            procurement_request=procurement_request,
        )

        response = client.post(
            f"/api/v1/procurement-requests/{eligibility_test_data['request_id']}/recommendations"
        )

        assert response.status_code == 200
        api_result = response.json()

        assert api_result["procurement_request_id"] == str(
            service_result.procurement_request_id
        )
        assert (
            api_result["recommended_centre"]["centre_id"]
            == str(service_result.recommended_centre.centre_id)
        )
        assert (
            api_result["recommended_centre"]["score"]
            == pytest.approx(service_result.recommended_centre.score)
        )
        assert (
            api_result["recommended_centre"]["available_capacity"]
            == pytest.approx(service_result.recommended_centre.available_capacity)
        )
        assert (
            api_result["recommended_centre"]["reasons"]
            == service_result.recommended_centre.reasons
        )

    finally:
        db.close()


def test_recommendations_endpoint_rejects_non_requested_status(
    eligibility_test_data,
):
    """Verifies that non-REQUESTED status is rejected with HTTP 409."""
    factory = get_session_factory()
    db = factory()

    try:
        procurement_request = (
            db.query(ProcurementRequest)
            .filter(
                ProcurementRequest.id == eligibility_test_data["request_id"]
            )
            .one()
        )
        procurement_request.status = "SLOT_CONFIRMED"
        db.commit()

        response = client.post(
            f"/api/v1/procurement-requests/{eligibility_test_data['request_id']}/recommendations"
        )

        assert response.status_code == 409

    finally:
        db.close()


def test_recommendations_endpoint_invalid_uuid():
    """Verifies that an invalid UUID path parameter returns HTTP 422."""
    response = client.post(
        "/api/v1/procurement-requests/not-a-valid-uuid/recommendations"
    )

    assert response.status_code == 422
