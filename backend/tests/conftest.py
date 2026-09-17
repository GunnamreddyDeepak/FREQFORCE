import uuid

import pytest
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.session import get_session_factory
from app.models.commodity import Commodity
from app.models.farmer import Farmer
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