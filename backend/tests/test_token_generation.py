import concurrent.futures
from datetime import date
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
from app.models.procurement_request import (
    ProcurementRequest,
    ProcurementRequestStatus,
)
from app.models.token import Token, TokenStatus
from app.models.token_sequence import TokenSequence
from app.models.user import User
from app.services.centre_slot import generate_daily_slots
from app.services.token import allocate_token

client = TestClient(app)


def test_token_sequence_monotonicity():
    """Verifies that token sequence numbers allocate monotonically: 1, 2, 3."""
    factory = get_session_factory()
    db = factory()

    try:
        user = User(phone_number=f"994{uuid.uuid4().int % 10**7:07d}", role="FARMER", is_active=True)
        db.add(user)
        db.flush()
        farmer = Farmer(user_id=user.id, full_name="Mono Farmer", is_active=True)
        db.add(farmer)
        commodity = Commodity(commodity_code=f"MONO-{uuid.uuid4().hex[:6]}", name="Mono Commodity", is_active=True)
        db.add(commodity)
        centre = ProcurementCentre(
            centre_code=f"MONO-{uuid.uuid4().hex[:4].upper()}",
            name="Mono Centre",
            location="SRID=4326;POINT(80.2707 13.0827)",
            is_active=True,
        )
        db.add(centre)
        db.flush()

        target_date = date(2026, 9, 20)
        capacity = CentreCapacity(
            centre_id=centre.id,
            capacity_date=target_date,
            daily_quantity_capacity=Decimal("100.000"),
            committed_quantity=Decimal("0.000"),
            is_active=True,
        )
        db.add(capacity)
        db.flush()

        slots = generate_daily_slots(db=db, centre_id=centre.id, slot_date=target_date)
        db.commit()

        # Create 3 requests
        tokens = []
        for i in range(3):
            req = ProcurementRequest(
                farmer_id=farmer.id,
                commodity_id=commodity.id,
                requested_quantity=Decimal("5.000"),
                preferred_date=target_date,
                farmer_location=slots[0].centre.location,
                status="REQUESTED",
            )
            db.add(req)
            db.commit()

            tok = allocate_token(db=db, centre=centre, slot=slots[0], procurement_request=req)
            db.commit()
            tokens.append(tok)

        assert tokens[0].token_number.endswith("-001")
        assert tokens[1].token_number.endswith("-002")
        assert tokens[2].token_number.endswith("-003")

        seq_row = (
            db.query(TokenSequence)
            .filter(
                TokenSequence.centre_id == centre.id,
                TokenSequence.token_date == target_date,
            )
            .one()
        )
        assert seq_row.next_sequence == 4
    finally:
        db.close()


def test_concurrent_token_generation_uniqueness():
    """Verifies multithreaded concurrent token allocation produces zero duplicate sequence numbers."""
    factory = get_session_factory()
    db = factory()

    user = User(phone_number=f"991{uuid.uuid4().int % 10**7:07d}", role="FARMER", is_active=True)
    db.add(user)
    db.flush()
    farmer = Farmer(user_id=user.id, full_name="Conc Farmer", is_active=True)
    db.add(farmer)
    commodity = Commodity(commodity_code=f"CONC-{uuid.uuid4().hex[:6]}", name="Conc Commodity", is_active=True)
    db.add(commodity)
    centre = ProcurementCentre(
        centre_code=f"CONC-{uuid.uuid4().hex[:4].upper()}",
        name="Conc Centre",
        location="SRID=4326;POINT(80.2707 13.0827)",
        is_active=True,
    )
    db.add(centre)
    db.flush()

    capacity = CentreCapacity(
        centre_id=centre.id,
        capacity_date=date(2026, 9, 21),
        daily_quantity_capacity=Decimal("500.000"),
        committed_quantity=Decimal("0.000"),
        is_active=True,
    )
    db.add(capacity)
    db.flush()

    slots = generate_daily_slots(db=db, centre_id=centre.id, slot_date=date(2026, 9, 21))
    db.commit()

    # Create 10 requests
    requests = []
    for _ in range(10):
        req = ProcurementRequest(
            farmer_id=farmer.id,
            commodity_id=commodity.id,
            requested_quantity=Decimal("10.000"),
            preferred_date=date(2026, 9, 21),
            farmer_location=centre.location,
            status="REQUESTED",
        )
        db.add(req)
        db.flush()
        requests.append(req.id)
    db.commit()

    centre_id = centre.id
    slot_id = slots[0].id
    db.close()

    def allocate(req_id):
        s_db = factory()
        try:
            c = s_db.query(ProcurementCentre).filter(ProcurementCentre.id == centre_id).one()
            sl = s_db.query(CentreSlot).filter(CentreSlot.id == slot_id).one()
            r = s_db.query(ProcurementRequest).filter(ProcurementRequest.id == req_id).one()
            tok = allocate_token(db=s_db, centre=c, slot=sl, procurement_request=r)
            s_db.commit()
            return tok.token_number
        finally:
            s_db.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(allocate, rid) for rid in requests]
        token_numbers = [f.result() for f in concurrent.futures.as_completed(futures)]

    # Assert exactly 10 distinct token numbers
    assert len(token_numbers) == 10
    assert len(set(token_numbers)) == 10

    # Verify sequence values 001 to 010
    sequences = sorted([int(t.split("-")[-1]) for t in token_numbers])
    assert sequences == list(range(1, 11))


def test_slot_booking_auto_token_issuance_and_cancellation(eligibility_test_data):
    """Verifies that confirm-slot issues token, sets TOKEN_GENERATED, and cancellation releases all."""
    factory = get_session_factory()
    db = factory()

    try:
        centre_id = eligibility_test_data["centre_id"]
        request_id = eligibility_test_data["request_id"]
        target_date = date(2026, 9, 20)

        req = db.query(ProcurementRequest).filter(ProcurementRequest.id == request_id).one()
        req.requested_quantity = 15.0
        db.commit()

        slots = generate_daily_slots(db=db, centre_id=centre_id, slot_date=target_date)
        db.commit()
        target_slot = slots[0]

        # 1. Confirm Slot
        res = client.post(
            f"/api/v1/procurement-requests/{request_id}/confirm-slot",
            json={
                "centre_id": str(centre_id),
                "slot_id": str(target_slot.id),
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "TOKEN_GENERATED"
        assert data["token"] is not None
        assert data["token"]["status"] == "ACTIVE"
        token_id = data["token"]["id"]

        # 2. Verify Token row in DB
        db.expire_all()
        tok = db.query(Token).filter(Token.id == token_id).one()
        assert tok.status == "ACTIVE"
        assert tok.procurement_request_id == request_id

        # 3. Cancel Request
        res_cancel = client.post(f"/api/v1/procurement-requests/{request_id}/cancel")
        assert res_cancel.status_code == 200

        # Verify token marked CANCELLED
        db.expire_all()
        tok_reloaded = db.query(Token).filter(Token.id == token_id).one()
        assert tok_reloaded.status == "CANCELLED"
    finally:
        db.close()
