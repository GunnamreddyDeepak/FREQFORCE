"""Deterministic, idempotent development and demo seed script for KISANQUEUE.

Creates core master data:
1. Demo FARMER User and linked Farmer profile.
2. Active Commodities (Paddy, Wheat).
3. Active Procurement Centres (Miryalaguda, Suryapet, Kodad) with PostGIS Point locations.
4. CentreCommodity capability mappings (all handle Paddy, 2 handle Wheat).
5. CentreCapacity daily allocations for the target date (differentiated capacities).
6. CentreSlots for the target date (4 standard 2-hour non-overlapping windows per centre).

Usage:
    python scripts/seed_demo_data.py [--date YYYY-MM-DD]
"""

import argparse
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

# Add backend directory to sys.path so app imports work when executed directly
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from geoalchemy2 import WKTElement
from sqlalchemy.orm import Session

from app.db.session import get_session_factory
from app.models.centre_capacity import CentreCapacity
from app.models.centre_commodity import CentreCommodity
from app.models.centre_slot import CentreSlot
from app.models.commodity import Commodity
from app.models.farmer import Farmer
from app.models.procurement_centre import ProcurementCentre
from app.models.user import User, UserRole
from app.services.centre_slot import generate_daily_slots


DEMO_FARMER_USER = {
    "phone_number": "9876543210",
    "role": UserRole.FARMER.value,
    "is_active": True,
}

DEMO_FARMER_PROFILE = {
    "full_name": "Ramesh Kumar",
    "village": "Narsingi",
    "district": "Rangareddy",
    "state": "Telangana",
    "is_active": True,
}

DEMO_COMMODITIES = [
    {
        "commodity_code": "PADDY",
        "name": "Paddy (Common)",
        "is_active": True,
    },
    {
        "commodity_code": "WHEAT",
        "name": "Wheat (Standard)",
        "is_active": True,
    },
]

DEMO_CENTRES = [
    {
        "centre_code": "KQM-MIR-01",
        "name": "Miryalaguda Main Procurement Centre",
        "address": "Agricultural Market Yard, Miryalaguda",
        "district": "Nalgonda",
        "state": "Telangana",
        "longitude": 79.5638,
        "latitude": 16.8741,
        "daily_capacity": Decimal("500.000"),
        "commodities": ["PADDY", "WHEAT"],
    },
    {
        "centre_code": "KQM-SRY-02",
        "name": "Suryapet Agri Market Yard",
        "address": "Khammam Road, Suryapet",
        "district": "Suryapet",
        "state": "Telangana",
        "longitude": 79.6236,
        "latitude": 17.1439,
        "daily_capacity": Decimal("300.000"),
        "commodities": ["PADDY", "WHEAT"],
    },
    {
        "centre_code": "KQM-KDD-03",
        "name": "Kodad Farmer Support Centre",
        "address": "Huzurnagar Road, Kodad",
        "district": "Suryapet",
        "state": "Telangana",
        "longitude": 79.9678,
        "latitude": 16.9950,
        "daily_capacity": Decimal("200.000"),
        "commodities": ["PADDY"],
    },
]


def seed_demo_data(db: Session, target_date: Optional[date] = None) -> dict:
    """Idempotently seed demo data into the database."""
    if target_date is None:
        target_date = date.today()

    stats = {
        "users_created": 0,
        "users_existing": 0,
        "farmers_created": 0,
        "farmers_existing": 0,
        "commodities_created": 0,
        "commodities_existing": 0,
        "centres_created": 0,
        "centres_existing": 0,
        "capabilities_created": 0,
        "capabilities_existing": 0,
        "capacities_created": 0,
        "capacities_existing": 0,
        "slots_created": 0,
        "slots_existing": 0,
    }

    try:
        # 1. Seed Demo User
        user = (
            db.query(User)
            .filter(User.phone_number == DEMO_FARMER_USER["phone_number"])
            .first()
        )
        if user is None:
            user = User(
                phone_number=DEMO_FARMER_USER["phone_number"],
                role=DEMO_FARMER_USER["role"],
                is_active=DEMO_FARMER_USER["is_active"],
            )
            db.add(user)
            db.flush()
            stats["users_created"] += 1
        else:
            stats["users_existing"] += 1

        # 2. Seed Demo Farmer Profile
        farmer = (
            db.query(Farmer)
            .filter(Farmer.user_id == user.id)
            .first()
        )
        if farmer is None:
            farmer = Farmer(
                user_id=user.id,
                full_name=DEMO_FARMER_PROFILE["full_name"],
                village=DEMO_FARMER_PROFILE["village"],
                district=DEMO_FARMER_PROFILE["district"],
                state=DEMO_FARMER_PROFILE["state"],
                is_active=DEMO_FARMER_PROFILE["is_active"],
            )
            db.add(farmer)
            db.flush()
            stats["farmers_created"] += 1
        else:
            stats["farmers_existing"] += 1

        # 3. Seed Commodities
        commodity_map = {}
        for c_data in DEMO_COMMODITIES:
            commodity = (
                db.query(Commodity)
                .filter(Commodity.commodity_code == c_data["commodity_code"])
                .first()
            )
            if commodity is None:
                commodity = Commodity(
                    commodity_code=c_data["commodity_code"],
                    name=c_data["name"],
                    is_active=c_data["is_active"],
                )
                db.add(commodity)
                db.flush()
                stats["commodities_created"] += 1
            else:
                stats["commodities_existing"] += 1
            commodity_map[c_data["commodity_code"]] = commodity

        # 4. Seed Procurement Centres, Capabilities, Capacities, and Slots
        for centre_spec in DEMO_CENTRES:
            centre = (
                db.query(ProcurementCentre)
                .filter(ProcurementCentre.centre_code == centre_spec["centre_code"])
                .first()
            )
            if centre is None:
                point_geom = WKTElement(
                    f"POINT({centre_spec['longitude']} {centre_spec['latitude']})",
                    srid=4326,
                )
                centre = ProcurementCentre(
                    centre_code=centre_spec["centre_code"],
                    name=centre_spec["name"],
                    address=centre_spec["address"],
                    district=centre_spec["district"],
                    state=centre_spec["state"],
                    location=point_geom,
                    is_active=True,
                )
                db.add(centre)
                db.flush()
                stats["centres_created"] += 1
            else:
                stats["centres_existing"] += 1

            # 5. Capabilities (CentreCommodity)
            for code in centre_spec["commodities"]:
                cmd = commodity_map[code]
                capability = (
                    db.query(CentreCommodity)
                    .filter(
                        CentreCommodity.centre_id == centre.id,
                        CentreCommodity.commodity_id == cmd.id,
                    )
                    .first()
                )
                if capability is None:
                    capability = CentreCommodity(
                        centre_id=centre.id,
                        commodity_id=cmd.id,
                        is_active=True,
                    )
                    db.add(capability)
                    db.flush()
                    stats["capabilities_created"] += 1
                else:
                    stats["capabilities_existing"] += 1

            # 6. Daily Capacity (CentreCapacity)
            capacity = (
                db.query(CentreCapacity)
                .filter(
                    CentreCapacity.centre_id == centre.id,
                    CentreCapacity.capacity_date == target_date,
                )
                .first()
            )
            if capacity is None:
                capacity = CentreCapacity(
                    centre_id=centre.id,
                    capacity_date=target_date,
                    daily_quantity_capacity=centre_spec["daily_capacity"],
                    committed_quantity=Decimal("0.000"),
                    is_active=True,
                )
                db.add(capacity)
                db.flush()
                stats["capacities_created"] += 1
            else:
                stats["capacities_existing"] += 1

            # 7. Generate Daily Slots
            existing_slots_count = (
                db.query(CentreSlot)
                .filter(
                    CentreSlot.centre_id == centre.id,
                    CentreSlot.slot_date == target_date,
                )
                .count()
            )

            slots = generate_daily_slots(
                db=db,
                centre_id=centre.id,
                slot_date=target_date,
                daily_capacity=capacity.daily_quantity_capacity,
            )

            if existing_slots_count == 0:
                stats["slots_created"] += len(slots)
            else:
                stats["slots_existing"] += existing_slots_count

        db.commit()
        return stats
    except Exception:
        db.rollback()
        raise


def parse_date(date_str: str) -> date:
    """Parse YYYY-MM-DD string into a datetime.date object."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"Invalid date format: '{date_str}'. Expected YYYY-MM-DD.") from e


def main():
    parser = argparse.ArgumentParser(
        description="Seed KISANQUEUE development and demo data idempotently."
    )
    parser.add_argument(
        "--date",
        type=parse_date,
        default=date.today(),
        help="Target date for capacity and slot generation (YYYY-MM-DD). Default: today.",
    )
    args = parser.parse_args()

    session_factory = get_session_factory()
    db = session_factory()

    try:
        print(f"[*] Starting KISANQUEUE demo data seed for date: {args.date}...")
        stats = seed_demo_data(db=db, target_date=args.date)

        print("\n[+] Demo Data Seed Completed Successfully!")
        print("--------------------------------------------------")
        print(f"Users:        {stats['users_created']} created, {stats['users_existing']} already existed")
        print(f"Farmers:      {stats['farmers_created']} created, {stats['farmers_existing']} already existed")
        print(f"Commodities:  {stats['commodities_created']} created, {stats['commodities_existing']} already existed")
        print(f"Centres:      {stats['centres_created']} created, {stats['centres_existing']} already existed")
        print(f"Capabilities: {stats['capabilities_created']} created, {stats['capabilities_existing']} already existed")
        print(f"Capacities:   {stats['capacities_created']} created, {stats['capacities_existing']} already existed")
        print(f"Slots:        {stats['slots_created']} created, {stats['slots_existing']} already existed")
        print("--------------------------------------------------")
    except Exception as exc:
        print(f"\n[!] Error during demo data seeding: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
