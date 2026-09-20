from datetime import date, datetime, time, timezone
from decimal import Decimal
import uuid

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_session_factory
from app.main import app
from app.models.centre_capacity import CentreCapacity
from app.models.centre_slot import CentreSlot
from app.models.procurement_centre import ProcurementCentre
from app.models.procurement_request import ProcurementRequest
from app.models.queue_entry import QueueEntry, QueueStatus
from app.models.token import Token, TokenStatus
from app.services.centre_slot import generate_daily_slots

client = TestClient(app)


def test_gate_check_in_success(eligibility_test_data):
    """Verifies that valid gate check-in transitions request to CHECKED_IN, token to USED, and creates WAITING QueueEntry."""
    factory = get_session_factory()
    db = factory()

    try:
        centre_id = eligibility_test_data["centre_id"]
        request_id = eligibility_test_data["request_id"]
        target_date = date(2026, 9, 20)

        req = db.query(ProcurementRequest).filter(ProcurementRequest.id == request_id).one()
        req.requested_quantity = 12.0
        db.commit()

        slots = generate_daily_slots(db=db, centre_id=centre_id, slot_date=target_date)
        db.commit()

        # 1. Confirm Slot
        res_book = client.post(
            f"/api/v1/procurement-requests/{request_id}/confirm-slot",
            json={"centre_id": str(centre_id), "slot_id": str(slots[0].id)},
        )
        assert res_book.status_code == 200
        token_number = res_book.json()["token"]["token_number"]

        # 2. Gate Check-In (On-Time)
        res_checkin = client.post(
            f"/api/v1/centres/{centre_id}/check-in",
            json={"token_number": token_number, "vehicle_number": "TS-08-TX-1234"},
        )
        assert res_checkin.status_code == 200
        data = res_checkin.json()
        assert data["token_number"] == token_number
        assert data["status"] == "WAITING"
        assert data["is_late"] is False
        assert data["dynamic_position"] == 1
        assert data["vehicle_number"] == "TS-08-TX-1234"

        # 3. Verify DB State
        db.expire_all()
        reloaded_req = db.query(ProcurementRequest).filter(ProcurementRequest.id == request_id).one()
        assert reloaded_req.status == "CHECKED_IN"

        reloaded_tok = db.query(Token).filter(Token.token_number == token_number).one()
        assert reloaded_tok.status == "USED"

        queue_entry = db.query(QueueEntry).filter(QueueEntry.id == data["queue_entry_id"]).one()
        assert queue_entry.status == "WAITING"
        assert queue_entry.is_late is False

        # 4. Check-In Idempotency: Re-submitting check-in for same token returns 200 with existing entry
        res_replay = client.post(
            f"/api/v1/centres/{centre_id}/check-in",
            json={"token_number": token_number, "vehicle_number": "TS-08-TX-1234"},
        )
        assert res_replay.status_code == 200
        assert res_replay.json()["queue_entry_id"] == data["queue_entry_id"]
    finally:
        db.close()


def test_gate_check_in_wrong_centre_and_unknown_token(eligibility_test_data):
    """Verifies that wrong centre returns 400 and unknown token returns 404."""
    factory = get_session_factory()
    db = factory()

    try:
        centre_id = eligibility_test_data["centre_id"]
        request_id = eligibility_test_data["request_id"]
        target_date = date(2026, 9, 20)

        req = db.query(ProcurementRequest).filter(ProcurementRequest.id == request_id).one()
        req.requested_quantity = 10.0
        db.commit()

        slots = generate_daily_slots(db=db, centre_id=centre_id, slot_date=target_date)
        db.commit()

        res_book = client.post(
            f"/api/v1/procurement-requests/{request_id}/confirm-slot",
            json={"centre_id": str(centre_id), "slot_id": str(slots[0].id)},
        )
        assert res_book.status_code == 200
        token_number = res_book.json()["token"]["token_number"]

        # 1. Unknown Token
        res_unknown = client.post(
            f"/api/v1/centres/{centre_id}/check-in",
            json={"token_number": "KQ-UNKNOWN-000"},
        )
        assert res_unknown.status_code == 404

        # 2. Wrong Centre
        random_centre_id = uuid.uuid4()
        res_wrong_centre = client.post(
            f"/api/v1/centres/{random_centre_id}/check-in",
            json={"token_number": token_number},
        )
        assert res_wrong_centre.status_code == 400
    finally:
        db.close()


def test_gate_check_in_late_arrival_classification(eligibility_test_data):
    """Verifies that check-in after slot end time sets is_late=True."""
    factory = get_session_factory()
    db = factory()

    try:
        centre_id = eligibility_test_data["centre_id"]
        request_id = eligibility_test_data["request_id"]
        target_date = date(2026, 9, 20)

        req = db.query(ProcurementRequest).filter(ProcurementRequest.id == request_id).one()
        req.requested_quantity = 10.0
        db.commit()

        slots = generate_daily_slots(db=db, centre_id=centre_id, slot_date=target_date)
        db.commit()
        # Slot 0 is 09:00 - 11:00
        target_slot = slots[0]

        res_book = client.post(
            f"/api/v1/procurement-requests/{request_id}/confirm-slot",
            json={"centre_id": str(centre_id), "slot_id": str(target_slot.id)},
        )
        assert res_book.status_code == 200
        token_number = res_book.json()["token"]["token_number"]

        from app.schemas.queue import CheckInRequest
        from app.services.check_in import gate_check_in

        # Simulate late check-in at 11:15:00 UTC on slot_date
        late_time = datetime.combine(target_date, time(11, 15, 0), tzinfo=timezone.utc)
        check_in_res = gate_check_in(
            db=db,
            centre_id=centre_id,
            check_in_data=CheckInRequest(token_number=token_number),
            check_in_time_override=late_time,
        )

        assert check_in_res.is_late is True
        assert check_in_res.status == "WAITING"
    finally:
        db.close()
