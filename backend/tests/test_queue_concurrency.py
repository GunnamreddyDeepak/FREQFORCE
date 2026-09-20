import concurrent.futures
from datetime import date, datetime, time, timezone
from decimal import Decimal
import uuid

import pytest

from app.db.session import get_session_factory
from app.models.centre_capacity import CentreCapacity
from app.models.centre_commodity import CentreCommodity
from app.models.centre_slot import CentreSlot
from app.models.commodity import Commodity
from app.models.farmer import Farmer
from app.models.procurement_centre import ProcurementCentre
from app.models.procurement_request import ProcurementRequest
from app.models.user import User
from app.schemas.queue import CallNextRequest, CheckInRequest
from app.services.centre_slot import generate_daily_slots
from app.services.check_in import gate_check_in
from app.services.queue import call_next_queue_entry
from app.services.slot_booking import confirm_procurement_slot


def test_concurrent_call_next_isolation_skip_locked():
    """Verifies that multiple operators calling call-next simultaneously receive distinct queue entries."""
    factory = get_session_factory()
    db = factory()

    user = User(phone_number=f"993{uuid.uuid4().int % 10**7:07d}", role="FARMER", is_active=True)
    db.add(user)
    db.flush()
    farmer = Farmer(user_id=user.id, full_name="Desk Concurrency Farmer", is_active=True)
    db.add(farmer)
    commodity = Commodity(commodity_code=f"DESK-{uuid.uuid4().hex[:6]}", name="Desk Commodity", is_active=True)
    db.add(commodity)
    centre = ProcurementCentre(
        centre_code=f"DSK-{uuid.uuid4().hex[:4].upper()}",
        name="Desk Centre",
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

    target_date = date(2026, 9, 23)
    capacity = CentreCapacity(
        centre_id=centre.id,
        capacity_date=target_date,
        daily_quantity_capacity=Decimal("500.000"),
        committed_quantity=Decimal("0.000"),
        is_active=True,
    )
    db.add(capacity)
    db.flush()

    slots = generate_daily_slots(db=db, centre_id=centre.id, slot_date=target_date)
    db.commit()
    target_slot = slots[0]  # 09:00 - 11:00

    # Create & Check In 5 Farmers
    tokens = []
    for i in range(5):
        r = ProcurementRequest(
            farmer_id=farmer.id,
            commodity_id=commodity.id,
            requested_quantity=Decimal("10.000"),
            preferred_date=target_date,
            farmer_location=centre.location,
            status="REQUESTED",
        )
        db.add(r)
        db.flush()

        booking = confirm_procurement_slot(db, r.id, centre.id, target_slot.id)
        ci = gate_check_in(
            db,
            centre.id,
            CheckInRequest(token_number=booking.token.token_number),
            check_in_time_override=datetime.combine(target_date, time(9, i * 5, 0), tzinfo=timezone.utc),
        )
        tokens.append(booking.token.token_number)

    db.commit()
    centre_id = centre.id
    db.close()

    # Simulate 5 operators simultaneously calling next
    t_call = datetime.combine(target_date, time(9, 30, 0), tzinfo=timezone.utc)

    def operator_call(desk_name):
        s_db = factory()
        try:
            called_entry = call_next_queue_entry(
                db=s_db,
                centre_id=centre_id,
                request_data=CallNextRequest(counter_or_bay=desk_name),
                current_time_override=t_call,
            )
            return called_entry.token_number
        finally:
            s_db.close()

    desks = [f"BAY-{i+1}" for i in range(5)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(operator_call, d) for d in desks]
        called_tokens = [f.result() for f in concurrent.futures.as_completed(futures)]

    # Assert all 5 distinct tokens were called without duplicate dispatch
    assert len(called_tokens) == 5
    assert set(called_tokens) == set(tokens)
