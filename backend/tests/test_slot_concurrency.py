import concurrent.futures
from datetime import date
from decimal import Decimal
import uuid

import pytest
from fastapi.testclient import TestClient
from geoalchemy2 import WKTElement
from sqlalchemy import delete

from app.db.session import get_session_factory
from app.main import app
from app.models.centre_capacity import CentreCapacity
from app.models.centre_commodity import CentreCommodity
from app.models.centre_slot import CentreSlot
from app.models.commodity import Commodity
from app.models.farmer import Farmer
from app.models.procurement_centre import ProcurementCentre
from app.models.procurement_request import ProcurementRequest
from app.models.user import User
from app.services.centre_slot import generate_daily_slots


def test_concurrent_slot_booking_atomicity():
    """Verifies that concurrent requests competing for limited slot capacity never overbook."""
    factory = get_session_factory()
    db = factory()

    # 1. Setup isolated centre, commodity, capacity
    user = User(phone_number=f"991{uuid.uuid4().int % 10**7:07d}", role="FARMER", is_active=True)
    db.add(user)
    db.flush()

    farmer = Farmer(user_id=user.id, full_name="Concurrency Farmer", is_active=True)
    db.add(farmer)
    db.flush()

    commodity = Commodity(commodity_code=f"CONC-{uuid.uuid4().hex[:6].upper()}", name="Conc Commodity", is_active=True)
    db.add(commodity)
    db.flush()

    centre = ProcurementCentre(
        centre_code=f"CONC-{uuid.uuid4().hex[:6].upper()}",
        name="Concurrency Centre",
        location=WKTElement("POINT(80.2707 13.0827)", srid=4326),
        is_active=True,
    )
    db.add(centre)
    db.flush()

    capability = CentreCommodity(centre_id=centre.id, commodity_id=commodity.id, is_active=True)
    db.add(capability)

    # 100 quintals daily capacity -> 25 quintals per slot
    capacity = CentreCapacity(
        centre_id=centre.id,
        capacity_date=date(2026, 9, 20),
        daily_quantity_capacity=Decimal("100.000"),
        committed_quantity=Decimal("0.000"),
        is_active=True,
    )
    db.add(capacity)
    db.flush()

    # Create 5 requests for 10 quintals each (only 2 can fit in a 25 qtl slot)
    request_ids = []
    for _ in range(5):
        req = ProcurementRequest(
            farmer_id=farmer.id,
            commodity_id=commodity.id,
            requested_quantity=Decimal("10.000"),
            preferred_date=date(2026, 9, 20),
            farmer_location=WKTElement("POINT(80.2707 13.0827)", srid=4326),
            status="REQUESTED",
        )
        db.add(req)
        db.flush()
        request_ids.append(req.id)

    db.commit()

    slots = generate_daily_slots(db=db, centre_id=centre.id, slot_date=date(2026, 9, 20))
    db.commit()
    target_slot_id = slots[0].id
    centre_id = centre.id
    capacity_id = capacity.id
    farmer_id = farmer.id
    user_id = user.id
    commodity_id = commodity.id
    db.close()

    # 2. Execute 5 concurrent booking calls
    def book_slot(req_id):
        client = TestClient(app)
        return client.post(
            f"/api/v1/procurement-requests/{req_id}/confirm-slot",
            json={
                "centre_id": str(centre_id),
                "slot_id": str(target_slot_id),
            },
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(book_slot, rid) for rid in request_ids]
        responses = [f.result() for f in concurrent.futures.as_completed(futures)]

    success_responses = [r for r in responses if r.status_code == 200]
    rejected_responses = [r for r in responses if r.status_code == 422]

    # Exactly 2 should succeed (2 * 10 = 20 <= 25), and 3 must be rejected (3rd needs 30 > 25)
    assert len(success_responses) == 2
    assert len(rejected_responses) == 3

    # 3. Verify final DB state respects invariants
    db_verify = factory()
    try:
        final_slot = db_verify.query(CentreSlot).filter(CentreSlot.id == target_slot_id).one()
        assert final_slot.booked_quantity == Decimal("20.000")
        assert final_slot.booked_quantity <= final_slot.quantity_capacity
        assert final_slot.booked_bookings == 2
        assert final_slot.booked_bookings <= final_slot.max_bookings

        final_cap = db_verify.query(CentreCapacity).filter(CentreCapacity.id == capacity_id).one()
        assert final_cap.committed_quantity == Decimal("20.000")
        assert final_cap.committed_quantity <= final_cap.daily_quantity_capacity
    finally:
        # Cleanup
        db_verify.execute(delete(ProcurementRequest).where(ProcurementRequest.farmer_id == farmer_id))
        db_verify.execute(delete(CentreSlot).where(CentreSlot.centre_id == centre_id))
        db_verify.execute(delete(CentreCapacity).where(CentreCapacity.centre_id == centre_id))
        db_verify.execute(delete(CentreCommodity).where(CentreCommodity.centre_id == centre_id))
        db_verify.execute(delete(ProcurementCentre).where(ProcurementCentre.id == centre_id))
        db_verify.execute(delete(Farmer).where(Farmer.id == farmer_id))
        db_verify.execute(delete(Commodity).where(Commodity.id == commodity_id))
        db_verify.execute(delete(User).where(User.id == user_id))
        db_verify.commit()
        db_verify.close()
