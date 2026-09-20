from datetime import date, datetime, time, timezone
from decimal import Decimal
import uuid

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_session_factory
from app.main import app
from app.models.centre_capacity import CentreCapacity
from app.models.centre_commodity import CentreCommodity
from app.models.centre_slot import CentreSlot
from app.models.commodity import Commodity
from app.models.farmer import Farmer
from app.models.procurement_centre import ProcurementCentre
from app.models.procurement_request import ProcurementRequest
from app.models.queue_entry import QueueEntry, QueueStatus
from app.models.token import Token, TokenStatus
from app.models.user import User
from app.schemas.queue import CallNextRequest, CheckInRequest, QueueStatusUpdateRequest
from app.services.centre_slot import generate_daily_slots
from app.services.check_in import gate_check_in
from app.services.queue import (
    call_next_queue_entry,
    get_centre_queue,
    update_queue_entry_status,
)
from app.services.slot_booking import confirm_procurement_slot

client = TestClient(app)


def test_queue_dynamic_ordering_and_future_slot_protection():
    """Validates 4-tier queue ordering and verifies future-slot farmer cannot be called early."""
    factory = get_session_factory()
    db = factory()

    user = User(phone_number=f"992{uuid.uuid4().int % 10**7:07d}", role="FARMER", is_active=True)
    db.add(user)
    db.flush()
    farmer = Farmer(user_id=user.id, full_name="Queue Test Farmer", is_active=True)
    db.add(farmer)
    commodity = Commodity(commodity_code=f"QCOM-{uuid.uuid4().hex[:6]}", name="Queue Commodity", is_active=True)
    db.add(commodity)
    centre = ProcurementCentre(
        centre_code=f"QCTR-{uuid.uuid4().hex[:4].upper()}",
        name="Queue Centre",
        location="SRID=4326;POINT(80.2707 13.0827)",
        is_active=True,
    )
    db.add(centre)
    db.flush()

    capability = CentreCommodity(
        centre_id=centre.id,
        commodity_id=commodity.id,
        is_active=True,
    )
    db.add(capability)

    target_date = date(2026, 9, 22)
    capacity = CentreCapacity(
        centre_id=centre.id,
        capacity_date=target_date,
        daily_quantity_capacity=Decimal("500.000"),
        committed_quantity=Decimal("0.000"),
        is_active=True,
    )
    db.add(capacity)
    db.flush()

    # Slot 0: 09:00 - 11:00
    # Slot 1: 11:00 - 13:00
    # Slot 2: 13:00 - 15:00
    # Slot 3: 15:00 - 17:00
    slots = generate_daily_slots(db=db, centre_id=centre.id, slot_date=target_date)
    db.commit()

    # Create 4 Requests:
    # Farmer A: 11:00 slot, arrives 10:55 (on-time)
    # Farmer B: 11:00 slot, arrives 11:05 (on-time)
    # Farmer C: 13:00 slot, arrives 11:10 (early for 13:00 slot)
    # Farmer L1: 09:00 slot, arrives 11:15 (late for 09:00 slot)
    reqs = []
    for qty in [10.0, 10.0, 10.0, 10.0]:
        r = ProcurementRequest(
            farmer_id=farmer.id,
            commodity_id=commodity.id,
            requested_quantity=Decimal(str(qty)),
            preferred_date=target_date,
            farmer_location=centre.location,
            status="REQUESTED",
        )
        db.add(r)
        db.flush()
        reqs.append(r)
    db.commit()

    # Confirm Bookings:
    # reqs[0] -> Slot 1 (11:00)
    # reqs[1] -> Slot 1 (11:00)
    # reqs[2] -> Slot 2 (13:00)
    # reqs[3] -> Slot 0 (09:00)
    b0 = confirm_procurement_slot(db, reqs[0].id, centre.id, slots[1].id)
    b1 = confirm_procurement_slot(db, reqs[1].id, centre.id, slots[1].id)
    b2 = confirm_procurement_slot(db, reqs[2].id, centre.id, slots[2].id)
    b3 = confirm_procurement_slot(db, reqs[3].id, centre.id, slots[0].id)

    # Check In with specific timestamps:
    t_A = datetime.combine(target_date, time(10, 55, 0), tzinfo=timezone.utc)
    t_B = datetime.combine(target_date, time(11, 5, 0), tzinfo=timezone.utc)
    t_C = datetime.combine(target_date, time(11, 10, 0), tzinfo=timezone.utc)
    t_L1 = datetime.combine(target_date, time(11, 15, 0), tzinfo=timezone.utc)

    ci_A = gate_check_in(db, centre.id, CheckInRequest(token_number=b0.token.token_number), check_in_time_override=t_A)
    ci_B = gate_check_in(db, centre.id, CheckInRequest(token_number=b1.token.token_number), check_in_time_override=t_B)
    ci_C = gate_check_in(db, centre.id, CheckInRequest(token_number=b2.token.token_number), check_in_time_override=t_C)
    ci_L1 = gate_check_in(db, centre.id, CheckInRequest(token_number=b3.token.token_number), check_in_time_override=t_L1)

    assert ci_A.is_late is False
    assert ci_B.is_late is False
    assert ci_C.is_late is False
    assert ci_L1.is_late is True

    # 1. Verify Dynamic Queue Ordering:
    # Expected order:
    # 1. Farmer A (11:00 slot, on-time, 10:55)
    # 2. Farmer B (11:00 slot, on-time, 11:05)
    # 3. Farmer C (13:00 slot, on-time, 11:10)
    # 4. Farmer L1 (09:00 slot, late, 11:15)
    queue_res = get_centre_queue(db=db, centre_id=centre.id, queue_date=target_date)
    assert queue_res.total_waiting == 4
    ordered_tokens = [e.token_number for e in queue_res.entries]
    assert ordered_tokens == [
        b0.token.token_number,
        b1.token.token_number,
        b2.token.token_number,
        b3.token.token_number,
    ]

    # 2. Operational Rule Verification for call-next:
    # Current time is 11:20:00 (during 11:00 - 13:00 window).
    # Callable entries:
    # - Farmer A (11:00 slot started) -> YES
    # - Farmer B (11:00 slot started) -> YES
    # - Farmer C (13:00 slot has NOT started!) -> NO (Future-slot farmer must not be called early)
    # - Farmer L1 (09:00 slot is late / expired) -> YES
    t_call = datetime.combine(target_date, time(11, 20, 0), tzinfo=timezone.utc)

    # Call 1: Should be Farmer A
    c1 = call_next_queue_entry(db, centre.id, CallNextRequest(counter_or_bay="BAY-1"), current_time_override=t_call)
    assert c1.token_number == b0.token.token_number
    assert c1.status == "CALLED"
    assert c1.counter_or_bay == "BAY-1"

    # Call 2: Should be Farmer B
    c2 = call_next_queue_entry(db, centre.id, CallNextRequest(counter_or_bay="BAY-2"), current_time_override=t_call)
    assert c2.token_number == b1.token.token_number

    # Call 3: Should be Farmer L1 (latecomer from expired 09:00 slot, NOT Farmer C whose 13:00 slot hasn't started)
    c3 = call_next_queue_entry(db, centre.id, CallNextRequest(counter_or_bay="BAY-1"), current_time_override=t_call)
    assert c3.token_number == b3.token.token_number

    # Call 4: At 11:20:00, Farmer C is in the 13:00 slot so no callable entries remain -> HTTP 404
    with pytest.raises(Exception) as exc:
        call_next_queue_entry(db, centre.id, CallNextRequest(counter_or_bay="BAY-1"), current_time_override=t_call)
    assert "No callable waiting entries" in str(exc.value.detail)

    # Advance time to 13:05:00 (13:00 slot starts)
    t_afternoon = datetime.combine(target_date, time(13, 5, 0), tzinfo=timezone.utc)
    c4 = call_next_queue_entry(db, centre.id, CallNextRequest(counter_or_bay="BAY-1"), current_time_override=t_afternoon)
    assert c4.token_number == b2.token.token_number
    assert c4.status == "CALLED"

    db.close()


def test_queue_status_transitions_and_cancellation(eligibility_test_data):
    """Verifies complete queue lifecycle (CALLED -> PROCESSING -> COMPLETED) and post-check-in cancellation."""
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

        # Confirm & Check In
        b = confirm_procurement_slot(db, request_id, centre_id, slots[0].id)
        ci = gate_check_in(db, centre_id, CheckInRequest(token_number=b.token.token_number))
        queue_entry_id = ci.queue_entry_id

        # 1. Call
        called = update_queue_entry_status(
            db=db,
            centre_id=centre_id,
            queue_entry_id=queue_entry_id,
            update_data=QueueStatusUpdateRequest(status="CALLED", counter_or_bay="BAY-1"),
        )
        assert called.status == "CALLED"

        # 2. Start Processing
        proc = update_queue_entry_status(
            db=db,
            centre_id=centre_id,
            queue_entry_id=queue_entry_id,
            update_data=QueueStatusUpdateRequest(status="PROCESSING"),
        )
        assert proc.status == "PROCESSING"

        # 3. Complete
        comp = update_queue_entry_status(
            db=db,
            centre_id=centre_id,
            queue_entry_id=queue_entry_id,
            update_data=QueueStatusUpdateRequest(status="COMPLETED"),
        )
        assert comp.status == "COMPLETED"

        # 4. Cancellation after completion must be rejected (409)
        from app.services.slot_booking import cancel_procurement_request
        with pytest.raises(Exception) as exc:
            cancel_procurement_request(db=db, request_id=request_id)
        assert "Cannot cancel" in str(exc.value.detail)
    finally:
        db.close()
