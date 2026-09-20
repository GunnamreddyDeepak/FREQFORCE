from datetime import date, time
from decimal import Decimal
import uuid

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_session_factory
from app.main import app
from app.models.centre_capacity import CentreCapacity
from app.models.centre_slot import CentreSlot
from app.services.centre_slot import generate_daily_slots, get_centre_slots

client = TestClient(app)


def test_slot_generation_exact_4_windows(eligibility_test_data):
    """Verifies that generate_daily_slots creates exactly 4 non-overlapping 2-hour windows."""
    factory = get_session_factory()
    db = factory()

    try:
        centre_id = eligibility_test_data["centre_id"]
        target_date = date(2026, 9, 20)

        slots = generate_daily_slots(
            db=db,
            centre_id=centre_id,
            slot_date=target_date,
        )

        assert len(slots) == 4
        assert [s.start_time for s in slots] == [
            time(9, 0),
            time(11, 0),
            time(13, 0),
            time(15, 0),
        ]
        assert [s.end_time for s in slots] == [
            time(11, 0),
            time(13, 0),
            time(15, 0),
            time(17, 0),
        ]

        # 100 quintals / 4 = 25.000 quintals per slot
        for s in slots:
            assert s.quantity_capacity == Decimal("25.000")
            assert s.booked_quantity == Decimal("0.000")
            assert s.max_bookings == 20
            assert s.booked_bookings == 0
            assert s.status == "AVAILABLE"
    finally:
        db.close()


def test_slot_generation_is_idempotent(eligibility_test_data):
    """Verifies that re-running slot generation does not create duplicate slots."""
    factory = get_session_factory()
    db = factory()

    try:
        centre_id = eligibility_test_data["centre_id"]
        target_date = date(2026, 9, 20)

        slots_first = generate_daily_slots(
            db=db,
            centre_id=centre_id,
            slot_date=target_date,
        )
        db.commit()

        slots_second = generate_daily_slots(
            db=db,
            centre_id=centre_id,
            slot_date=target_date,
        )
        db.commit()

        total_in_db = (
            db.query(CentreSlot)
            .filter(
                CentreSlot.centre_id == centre_id,
                CentreSlot.slot_date == target_date,
            )
            .count()
        )

        assert total_in_db == 4
        assert [s.id for s in slots_first] == [s.id for s in slots_second]
    finally:
        db.close()


def test_slot_generation_uses_decimal_division(eligibility_test_data):
    """Verifies capacity slicing using Decimal arithmetic for non-round numbers."""
    factory = get_session_factory()
    db = factory()

    try:
        centre_id = eligibility_test_data["centre_id"]
        target_date = date(2026, 9, 20)

        # Update capacity to 105.5 quintals
        cap = (
            db.query(CentreCapacity)
            .filter(
                CentreCapacity.centre_id == centre_id,
                CentreCapacity.capacity_date == target_date,
            )
            .one()
        )
        cap.daily_quantity_capacity = Decimal("105.500")
        db.commit()

        # Delete existing slots if any
        db.query(CentreSlot).filter(
            CentreSlot.centre_id == centre_id,
            CentreSlot.slot_date == target_date,
        ).delete()
        db.commit()

        slots = generate_daily_slots(
            db=db,
            centre_id=centre_id,
            slot_date=target_date,
        )

        # 105.500 / 4 = 26.375
        for s in slots:
            assert s.quantity_capacity == Decimal("26.375")
    finally:
        db.close()


def test_get_centre_slots_endpoint_returns_slots(eligibility_test_data):
    """Verifies GET /api/v1/centres/{centre_id}/slots endpoint."""
    centre_id = eligibility_test_data["centre_id"]
    response = client.get(f"/api/v1/centres/{centre_id}/slots?date=2026-09-20")

    assert response.status_code == 200
    data = response.json()

    assert data["centre_id"] == str(centre_id)
    assert data["centre_name"] == "Eligibility Test Centre"
    assert data["date"] == "2026-09-20"
    assert data["daily_capacity_qtl"] == 100.0
    assert len(data["slots"]) == 4

    slot0 = data["slots"][0]
    assert slot0["start_time"] == "09:00:00"
    assert slot0["end_time"] == "11:00:00"
    assert slot0["quantity_capacity"] == 25.0
    assert slot0["booked_quantity"] == 0.0
    assert slot0["remaining_quantity"] == 25.0
    assert slot0["max_bookings"] == 20
    assert slot0["booked_bookings"] == 0
    assert slot0["remaining_bookings"] == 20
    assert slot0["status"] == "AVAILABLE"


def test_get_centre_slots_unknown_centre():
    """Verifies 404 for non-existent centre ID."""
    unknown_id = uuid.uuid4()
    response = client.get(f"/api/v1/centres/{unknown_id}/slots?date=2026-09-20")
    assert response.status_code == 404


def test_get_centre_slots_missing_capacity_date(eligibility_test_data):
    """Verifies 404 when querying a date without capacity configuration."""
    centre_id = eligibility_test_data["centre_id"]
    response = client.get(f"/api/v1/centres/{centre_id}/slots?date=2030-01-01")
    assert response.status_code == 404
