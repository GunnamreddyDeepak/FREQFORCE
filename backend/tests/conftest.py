import uuid
from datetime import date

import pytest
from geoalchemy2 import WKTElement
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.session import get_session_factory
from app.models.centre_capacity import CentreCapacity
from app.models.centre_commodity import CentreCommodity
from app.models.commodity import Commodity
from app.models.farmer import Farmer
from app.models.procurement_centre import ProcurementCentre
from app.models.procurement_request import ProcurementRequest
from app.models.user import User


@pytest.fixture
def procurement_test_data():
    """Creates and cleans up isolated data for procurement integration tests."""

    factory = get_session_factory()
    db: Session = factory()

    user = User(
        phone_number=f"999{uuid.uuid4().int % 10**7:07d}",
        role="FARMER",
        is_active=True,
    )
    db.add(user)
    db.flush()

    farmer = Farmer(
        user_id=user.id,
        full_name="Integration Test Farmer",
        village="Test Village",
        district="Test District",
        state="Test State",
        is_active=True,
    )
    db.add(farmer)

    commodity = Commodity(
        commodity_code=f"TEST-{uuid.uuid4().hex[:8].upper()}",
        name="Test Commodity",
        is_active=True,
    )
    db.add(commodity)

    db.commit()
    db.refresh(farmer)
    db.refresh(commodity)

    try:
        yield {
            "farmer_id": farmer.id,
            "commodity_id": commodity.id,
        }
    finally:
        db.execute(
            delete(ProcurementRequest).where(
                ProcurementRequest.farmer_id == farmer.id
            )
        )

        db.execute(
            delete(Farmer).where(
                Farmer.id == farmer.id
            )
        )

        db.execute(
            delete(Commodity).where(
                Commodity.id == commodity.id
            )
        )

        db.execute(
            delete(User).where(
                User.id == user.id
            )
        )

        db.commit()
        db.close()


@pytest.fixture
def eligibility_test_data():
    """Creates isolated centre, commodity, capability, capacity and request data."""

    factory = get_session_factory()
    db: Session = factory()

    user = User(
        phone_number=f"998{uuid.uuid4().int % 10**7:07d}",
        role="FARMER",
        is_active=True,
    )
    db.add(user)
    db.flush()

    farmer = Farmer(
        user_id=user.id,
        full_name="Eligibility Test Farmer",
        village="Eligibility Village",
        district="Test District",
        state="Test State",
        is_active=True,
    )
    db.add(farmer)
    db.flush()

    commodity = Commodity(
        commodity_code=f"ELIG-{uuid.uuid4().hex[:8].upper()}",
        name="Eligibility Commodity",
        is_active=True,
    )
    db.add(commodity)
    db.flush()

    centre = ProcurementCentre(
        centre_code=f"ELIG-{uuid.uuid4().hex[:8].upper()}",
        name="Eligibility Test Centre",
        address="Test Address",
        district="Test District",
        state="Test State",
        location=WKTElement(
            "POINT(80.2707 13.0827)",
            srid=4326,
        ),
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

    capacity = CentreCapacity(
        centre_id=centre.id,
        capacity_date=date(2026, 9, 20),
        daily_quantity_capacity=100,
        committed_quantity=20,
        is_active=True,
    )
    db.add(capacity)

    procurement_request = ProcurementRequest(
        farmer_id=farmer.id,
        commodity_id=commodity.id,
        requested_quantity=70,
        preferred_date=date(2026, 9, 20),
        farmer_location=WKTElement(
            "POINT(80.2707 13.0827)",
            srid=4326,
        ),
        status="REQUESTED",
    )
    db.add(procurement_request)

    db.commit()

    db.refresh(farmer)
    db.refresh(commodity)
    db.refresh(centre)
    db.refresh(capability)
    db.refresh(capacity)
    db.refresh(procurement_request)

    try:
        yield {
            "farmer_id": farmer.id,
            "commodity_id": commodity.id,
            "centre_id": centre.id,
            "capability_id": capability.id,
            "capacity_id": capacity.id,
            "request_id": procurement_request.id,
        }
    finally:
        db.execute(
            delete(ProcurementRequest).where(
                ProcurementRequest.id == procurement_request.id
            )
        )

        db.execute(
            delete(CentreCapacity).where(
                CentreCapacity.id == capacity.id
            )
        )

        db.execute(
            delete(CentreCommodity).where(
                CentreCommodity.id == capability.id
            )
        )

        db.execute(
            delete(ProcurementCentre).where(
                ProcurementCentre.id == centre.id
            )
        )

        db.execute(
            delete(Farmer).where(
                Farmer.id == farmer.id
            )
        )

        db.execute(
            delete(Commodity).where(
                Commodity.id == commodity.id
            )
        )

        db.execute(
            delete(User).where(
                User.id == user.id
            )
        )

        db.commit()
        db.close()