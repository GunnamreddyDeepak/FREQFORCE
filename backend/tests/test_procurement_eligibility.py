from datetime import date

from fastapi.testclient import TestClient
from app.db.session import get_session_factory
from app.models.centre_capacity import CentreCapacity
from app.models.centre_commodity import CentreCommodity
from app.models.commodity import Commodity
from app.models.procurement_centre import ProcurementCentre
from app.models.procurement_request import ProcurementRequest
from app.services.procurement_eligibility import evaluate_eligible_centres
from app.main import app
import pytest
from fastapi import HTTPException

client = TestClient(app)


def get_request(db, request_id):
    return (
        db.query(ProcurementRequest).filter(ProcurementRequest.id == request_id).one()
    )


def test_eligible_centre_is_returned(eligibility_test_data):
    """Active centre with supported commodity and sufficient capacity is eligible."""

    factory = get_session_factory()
    db = factory()

    try:
        request = get_request(
            db,
            eligibility_test_data["request_id"],
        )

        result = evaluate_eligible_centres(db, request)

        assert result.procurement_request_id == request.id
        assert len(result.eligible_centres) == 1

        centre = result.eligible_centres[0]

        assert centre.centre_id == eligibility_test_data["centre_id"]
        assert centre.centre_code.startswith("ELIG-")
        assert centre.centre_name == "Eligibility Test Centre"
        assert centre.available_capacity == 80.0

        assert centre.reasons == [
            "CENTRE_ACTIVE",
            "COMMODITY_SUPPORTED",
            "CAPACITY_AVAILABLE",
        ]

    finally:
        db.close()


def test_unsupported_commodity_is_not_eligible(eligibility_test_data):
    """A centre that does not support the requested commodity is excluded."""

    factory = get_session_factory()
    db = factory()

    try:
        request = get_request(
            db,
            eligibility_test_data["request_id"],
        )

        capability = (
            db.query(CentreCommodity)
            .filter(CentreCommodity.id == eligibility_test_data["capability_id"])
            .one()
        )

        capability.is_active = False
        db.commit()

        result = evaluate_eligible_centres(db, request)

        assert result.eligible_centres == []

    finally:
        db.close()


def test_insufficient_capacity_is_not_eligible(eligibility_test_data):
    """A centre with insufficient remaining capacity is excluded."""

    factory = get_session_factory()
    db = factory()

    try:
        request = get_request(
            db,
            eligibility_test_data["request_id"],
        )

        capacity = (
            db.query(CentreCapacity)
            .filter(CentreCapacity.id == eligibility_test_data["capacity_id"])
            .one()
        )

        capacity.committed_quantity = 40
        db.commit()

        result = evaluate_eligible_centres(db, request)

        # 100 - 40 = 60 qtl available, but request needs 70 qtl.
        assert result.eligible_centres == []

    finally:
        db.close()


def test_missing_capacity_for_requested_date_is_not_eligible(
    eligibility_test_data,
):
    """A centre without active capacity for the requested date is excluded."""

    factory = get_session_factory()
    db = factory()

    try:
        request = get_request(
            db,
            eligibility_test_data["request_id"],
        )

        capacity = (
            db.query(CentreCapacity)
            .filter(CentreCapacity.id == eligibility_test_data["capacity_id"])
            .one()
        )

        capacity.capacity_date = date(2026, 9, 21)
        db.commit()

        result = evaluate_eligible_centres(db, request)

        assert result.eligible_centres == []

    finally:
        db.close()


def test_inactive_centre_is_not_eligible(eligibility_test_data):
    """An inactive procurement centre is excluded."""

    factory = get_session_factory()
    db = factory()

    try:
        request = get_request(
            db,
            eligibility_test_data["request_id"],
        )

        centre = (
            db.query(ProcurementCentre)
            .filter(ProcurementCentre.id == eligibility_test_data["centre_id"])
            .one()
        )

        centre.is_active = False
        db.commit()

        result = evaluate_eligible_centres(db, request)

        assert result.eligible_centres == []

    finally:
        db.close()


def test_non_requested_status_is_rejected(eligibility_test_data):
    """Eligibility evaluation only accepts requests in REQUESTED status."""

    factory = get_session_factory()
    db = factory()

    try:
        request = get_request(
            db,
            eligibility_test_data["request_id"],
        )

        request.status = "SLOT_CONFIRMED"
        db.commit()

        try:
            evaluate_eligible_centres(db, request)
            assert False, "Expected eligibility evaluation to reject the request"
        except Exception as exc:
            assert getattr(exc, "status_code", None) == 409

    finally:
        db.close()


def test_eligibility_endpoint_returns_eligible_centres(
    eligibility_test_data,
):
    """Verifies the HTTP eligibility endpoint returns eligible centres."""

    response = client.get(
        f"/api/v1/procurement-requests/"
        f"{eligibility_test_data['request_id']}/eligibility"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["procurement_request_id"] == str(eligibility_test_data["request_id"])

    assert len(data["eligible_centres"]) == 1

    centre = data["eligible_centres"][0]

    assert centre["centre_id"] == str(eligibility_test_data["centre_id"])
    assert centre["centre_code"].startswith("ELIG-")
    assert centre["centre_name"] == "Eligibility Test Centre"
    assert centre["available_capacity"] == 80.0
    assert centre["reasons"] == [
        "CENTRE_ACTIVE",
        "COMMODITY_SUPPORTED",
        "CAPACITY_AVAILABLE",
    ]


def test_eligibility_endpoint_returns_404_for_unknown_request():
    """Verifies an unknown procurement request returns HTTP 404."""

    import uuid

    response = client.get(f"/api/v1/procurement-requests/{uuid.uuid4()}/eligibility")

    assert response.status_code == 404
    assert response.json()["detail"] == "Procurement request not found"


def test_inactive_commodity_is_not_eligible(eligibility_test_data):
    """An inactive commodity is excluded from eligibility."""

    factory = get_session_factory()
    db = factory()

    try:
        request = get_request(
            db,
            eligibility_test_data["request_id"],
        )

        commodity = (
            db.query(Commodity)
            .filter(Commodity.id == eligibility_test_data["commodity_id"])
            .one()
        )

        commodity.is_active = False
        db.commit()

        result = evaluate_eligible_centres(db, request)

        assert result.eligible_centres == []

    finally:
        db.close()
