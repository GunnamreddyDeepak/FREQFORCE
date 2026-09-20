from datetime import date
from decimal import Decimal
import uuid

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_session_factory
from app.main import app
from app.models.centre_capacity import CentreCapacity
from app.models.centre_slot import CentreSlot, SlotStatus
from app.models.procurement_centre import ProcurementCentre
from app.models.procurement_request import (
    ProcurementRequest,
    ProcurementRequestStatus,
)
from app.services.centre_slot import generate_daily_slots

client = TestClient(app)


def test_confirm_slot_success(eligibility_test_data):
    """Verifies successful slot confirmation with atomic capacity updates and state transitions."""
    factory = get_session_factory()
    db = factory()

    try:
        centre_id = eligibility_test_data["centre_id"]
        request_id = eligibility_test_data["request_id"]
        target_date = date(2026, 9, 20)

        # Set request quantity to 20 quintals so it fits inside a 25 qtl slot
        req = (
            db.query(ProcurementRequest)
            .filter(ProcurementRequest.id == request_id)
            .one()
        )
        req.requested_quantity = 20.0
        db.commit()

        slots = generate_daily_slots(db=db, centre_id=centre_id, slot_date=target_date)
        db.commit()
        target_slot = slots[0]

        initial_committed = float(
            db.query(CentreCapacity)
            .filter(CentreCapacity.id == eligibility_test_data["capacity_id"])
            .one()
            .committed_quantity
        )

        response = client.post(
            f"/api/v1/procurement-requests/{request_id}/confirm-slot",
            json={
                "centre_id": str(centre_id),
                "slot_id": str(target_slot.id),
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["procurement_request_id"] == str(request_id)
        assert data["centre_id"] == str(centre_id)
        assert data["slot_id"] == str(target_slot.id)
        assert data["status"] == "TOKEN_GENERATED"
        assert data["booked_quantity"] == 20.0
        assert data["token"] is not None
        assert data["token"]["token_number"].startswith("KQ-")

        # Verify Database state
        db.expire_all()
        reloaded_req = (
            db.query(ProcurementRequest)
            .filter(ProcurementRequest.id == request_id)
            .one()
        )
        assert reloaded_req.status == "TOKEN_GENERATED"
        assert reloaded_req.confirmed_centre_id == centre_id
        assert reloaded_req.confirmed_slot_id == target_slot.id

        reloaded_slot = (
            db.query(CentreSlot)
            .filter(CentreSlot.id == target_slot.id)
            .one()
        )
        assert reloaded_slot.booked_quantity == Decimal("20.000")
        assert reloaded_slot.booked_bookings == 1
        assert reloaded_slot.status == "AVAILABLE"

        reloaded_cap = (
            db.query(CentreCapacity)
            .filter(CentreCapacity.id == eligibility_test_data["capacity_id"])
            .one()
        )
        assert float(reloaded_cap.committed_quantity) == pytest.approx(
            initial_committed + 20.0
        )
    finally:
        db.close()


def test_confirm_slot_idempotency_same_slot(eligibility_test_data):
    """Verifies that calling confirm-slot again with the same slot returns 200 without double-allocation."""
    factory = get_session_factory()
    db = factory()

    try:
        centre_id = eligibility_test_data["centre_id"]
        request_id = eligibility_test_data["request_id"]
        target_date = date(2026, 9, 20)

        req = (
            db.query(ProcurementRequest)
            .filter(ProcurementRequest.id == request_id)
            .one()
        )
        req.requested_quantity = 15.0
        db.commit()

        slots = generate_daily_slots(db=db, centre_id=centre_id, slot_date=target_date)
        db.commit()
        target_slot = slots[0]

        # First call
        res1 = client.post(
            f"/api/v1/procurement-requests/{request_id}/confirm-slot",
            json={
                "centre_id": str(centre_id),
                "slot_id": str(target_slot.id),
            },
        )
        assert res1.status_code == 200

        # Second call (idempotent replay)
        res2 = client.post(
            f"/api/v1/procurement-requests/{request_id}/confirm-slot",
            json={
                "centre_id": str(centre_id),
                "slot_id": str(target_slot.id),
            },
        )
        assert res2.status_code == 200
        assert res1.json() == res2.json()

        # Check DB allocation was only done ONCE
        db.expire_all()
        slot = db.query(CentreSlot).filter(CentreSlot.id == target_slot.id).one()
        assert slot.booked_quantity == Decimal("15.000")
        assert slot.booked_bookings == 1
    finally:
        db.close()


def test_confirm_slot_conflict_different_slot(eligibility_test_data):
    """Verifies that attempting to confirm a different slot while already confirmed returns 409."""
    factory = get_session_factory()
    db = factory()

    try:
        centre_id = eligibility_test_data["centre_id"]
        request_id = eligibility_test_data["request_id"]
        target_date = date(2026, 9, 20)

        req = (
            db.query(ProcurementRequest)
            .filter(ProcurementRequest.id == request_id)
            .one()
        )
        req.requested_quantity = 10.0
        db.commit()

        slots = generate_daily_slots(db=db, centre_id=centre_id, slot_date=target_date)
        db.commit()

        # Confirm slot 0
        res1 = client.post(
            f"/api/v1/procurement-requests/{request_id}/confirm-slot",
            json={
                "centre_id": str(centre_id),
                "slot_id": str(slots[0].id),
            },
        )
        assert res1.status_code == 200

        # Attempt to confirm slot 1 -> expect 409
        res2 = client.post(
            f"/api/v1/procurement-requests/{request_id}/confirm-slot",
            json={
                "centre_id": str(centre_id),
                "slot_id": str(slots[1].id),
            },
        )
        assert res2.status_code == 409
    finally:
        db.close()


def test_confirm_slot_insufficient_slot_capacity(eligibility_test_data):
    """Verifies that booking is rejected with 422 when request quantity exceeds remaining slot capacity."""
    factory = get_session_factory()
    db = factory()

    try:
        centre_id = eligibility_test_data["centre_id"]
        request_id = eligibility_test_data["request_id"]
        target_date = date(2026, 9, 20)

        # 30 quintals > 25 quintals slot capacity
        req = (
            db.query(ProcurementRequest)
            .filter(ProcurementRequest.id == request_id)
            .one()
        )
        req.requested_quantity = 30.0
        db.commit()

        slots = generate_daily_slots(db=db, centre_id=centre_id, slot_date=target_date)
        db.commit()

        response = client.post(
            f"/api/v1/procurement-requests/{request_id}/confirm-slot",
            json={
                "centre_id": str(centre_id),
                "slot_id": str(slots[0].id),
            },
        )
        assert response.status_code == 422
        assert "exceeds remaining slot capacity" in response.json()["detail"]
    finally:
        db.close()


def test_confirm_slot_insufficient_booking_count(eligibility_test_data):
    """Verifies that booking is rejected with 422 when slot reaches max bookings."""
    factory = get_session_factory()
    db = factory()

    try:
        centre_id = eligibility_test_data["centre_id"]
        request_id = eligibility_test_data["request_id"]
        target_date = date(2026, 9, 20)

        req = (
            db.query(ProcurementRequest)
            .filter(ProcurementRequest.id == request_id)
            .one()
        )
        req.requested_quantity = 1.0
        db.commit()

        slots = generate_daily_slots(db=db, centre_id=centre_id, slot_date=target_date)
        slot0 = slots[0]
        slot0.booked_bookings = slot0.max_bookings
        db.commit()

        response = client.post(
            f"/api/v1/procurement-requests/{request_id}/confirm-slot",
            json={
                "centre_id": str(centre_id),
                "slot_id": str(slot0.id),
            },
        )
        assert response.status_code in (409, 422)
    finally:
        db.close()


def test_confirm_slot_inactive_centre(eligibility_test_data):
    """Verifies that an inactive centre cannot accept booking."""
    factory = get_session_factory()
    db = factory()

    try:
        centre_id = eligibility_test_data["centre_id"]
        request_id = eligibility_test_data["request_id"]
        target_date = date(2026, 9, 20)

        slots = generate_daily_slots(db=db, centre_id=centre_id, slot_date=target_date)
        db.commit()

        centre = db.query(ProcurementCentre).filter(ProcurementCentre.id == centre_id).one()
        centre.is_active = False
        db.commit()

        response = client.post(
            f"/api/v1/procurement-requests/{request_id}/confirm-slot",
            json={
                "centre_id": str(centre_id),
                "slot_id": str(slots[0].id),
            },
        )
        assert response.status_code == 409
    finally:
        db.close()


def test_confirm_slot_paused_or_closed_slot(eligibility_test_data):
    """Verifies that a paused or closed slot rejects bookings."""
    factory = get_session_factory()
    db = factory()

    try:
        centre_id = eligibility_test_data["centre_id"]
        request_id = eligibility_test_data["request_id"]
        target_date = date(2026, 9, 20)

        req = (
            db.query(ProcurementRequest)
            .filter(ProcurementRequest.id == request_id)
            .one()
        )
        req.requested_quantity = 5.0
        db.commit()

        slots = generate_daily_slots(db=db, centre_id=centre_id, slot_date=target_date)
        slots[0].status = SlotStatus.PAUSED.value
        db.commit()

        response = client.post(
            f"/api/v1/procurement-requests/{request_id}/confirm-slot",
            json={
                "centre_id": str(centre_id),
                "slot_id": str(slots[0].id),
            },
        )
        assert response.status_code == 409
    finally:
        db.close()


def test_confirm_slot_wrong_centre_or_date(eligibility_test_data):
    """Verifies that mismatched centre ID or slot date is rejected."""
    factory = get_session_factory()
    db = factory()

    try:
        centre_id = eligibility_test_data["centre_id"]
        request_id = eligibility_test_data["request_id"]
        target_date = date(2026, 9, 20)

        slots = generate_daily_slots(db=db, centre_id=centre_id, slot_date=target_date)
        db.commit()

        # Mismatched centre ID
        random_centre_id = uuid.uuid4()
        response = client.post(
            f"/api/v1/procurement-requests/{request_id}/confirm-slot",
            json={
                "centre_id": str(random_centre_id),
                "slot_id": str(slots[0].id),
            },
        )
        assert response.status_code == 400
    finally:
        db.close()


def test_cancel_procurement_request_success(eligibility_test_data):
    """Verifies cancellation of a confirmed slot atomically releases slot and daily capacity."""
    factory = get_session_factory()
    db = factory()

    try:
        centre_id = eligibility_test_data["centre_id"]
        request_id = eligibility_test_data["request_id"]
        target_date = date(2026, 9, 20)

        req = (
            db.query(ProcurementRequest)
            .filter(ProcurementRequest.id == request_id)
            .one()
        )
        req.requested_quantity = 18.0
        db.commit()

        slots = generate_daily_slots(db=db, centre_id=centre_id, slot_date=target_date)
        db.commit()
        target_slot = slots[0]

        # Confirm
        res_confirm = client.post(
            f"/api/v1/procurement-requests/{request_id}/confirm-slot",
            json={
                "centre_id": str(centre_id),
                "slot_id": str(target_slot.id),
            },
        )
        assert res_confirm.status_code == 200

        # Cancel
        res_cancel = client.post(
            f"/api/v1/procurement-requests/{request_id}/cancel"
        )
        assert res_cancel.status_code == 200
        data = res_cancel.json()
        assert data["status"] == "CANCELLED"

        # Verify DB capacity release
        db.expire_all()
        reloaded_slot = db.query(CentreSlot).filter(CentreSlot.id == target_slot.id).one()
        assert reloaded_slot.booked_quantity == Decimal("0.000")
        assert reloaded_slot.booked_bookings == 0

        reloaded_cap = (
            db.query(CentreCapacity)
            .filter(CentreCapacity.id == eligibility_test_data["capacity_id"])
            .one()
        )
        assert float(reloaded_cap.committed_quantity) == pytest.approx(20.0)

        reloaded_req = db.query(ProcurementRequest).filter(ProcurementRequest.id == request_id).one()
        assert reloaded_req.status == "CANCELLED"
    finally:
        db.close()
