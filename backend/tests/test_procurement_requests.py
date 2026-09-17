from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import get_session_factory
from app.main import app

client = TestClient(app)


def test_create_procurement_request(procurement_test_data):
    """Verifies the complete procurement request creation flow."""

    farmer_id = procurement_test_data["farmer_id"]
    commodity_id = procurement_test_data["commodity_id"]

    response = client.post(
        "/api/v1/procurement-requests",
        json={
            "farmer_id": str(farmer_id),
            "commodity_id": str(commodity_id),
            "requested_quantity": 70,
            "preferred_date": "2026-09-20",
            "latitude": 13.0827,
            "longitude": 80.2707,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["farmer_id"] == str(farmer_id)
    assert data["commodity_id"] == str(commodity_id)
    assert data["requested_quantity"] == 70.0
    assert data["preferred_date"] == "2026-09-20"
    assert data["status"] == "REQUESTED"

    request_id = data["id"]

    factory = get_session_factory()
    db = factory()

    try:
        row = db.execute(
            text(
                """
                SELECT
                    requested_quantity,
                    preferred_date,
                    status,
                    ST_AsText(farmer_location) AS location
                FROM procurement_requests
                WHERE id = :request_id
                """
            ),
            {"request_id": request_id},
        ).mappings().one()

        assert float(row["requested_quantity"]) == 70.0
        assert row["preferred_date"] == date(2026, 9, 20)
        assert row["status"] == "REQUESTED"
        assert row["location"] == "POINT(80.2707 13.0827)"

    finally:
        db.close()


def test_create_procurement_request_rejects_invalid_quantity(
    procurement_test_data,
):
    """Verifies non-positive quantities are rejected."""

    response = client.post(
        "/api/v1/procurement-requests",
        json={
            "farmer_id": str(procurement_test_data["farmer_id"]),
            "commodity_id": str(procurement_test_data["commodity_id"]),
            "requested_quantity": 0,
            "preferred_date": "2026-09-20",
            "latitude": 13.0827,
            "longitude": 80.2707,
        },
    )

    assert response.status_code == 422


def test_create_procurement_request_rejects_invalid_coordinates(
    procurement_test_data,
):
    """Verifies invalid geographic coordinates are rejected."""

    response = client.post(
        "/api/v1/procurement-requests",
        json={
            "farmer_id": str(procurement_test_data["farmer_id"]),
            "commodity_id": str(procurement_test_data["commodity_id"]),
            "requested_quantity": 70,
            "preferred_date": "2026-09-20",
            "latitude": 100,
            "longitude": 200,
        },
    )

    assert response.status_code == 422