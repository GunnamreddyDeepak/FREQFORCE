"""Verification script testing the complete end-to-end KISANQUEUE workflow against seeded demo data."""

import sys
from datetime import date
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient

from app.db.session import get_session_factory
from app.main import app
from app.models.commodity import Commodity
from app.models.farmer import Farmer
from app.models.procurement_centre import ProcurementCentre
from app.models.user import User


def main():
    client = TestClient(app)
    factory = get_session_factory()
    db = factory()

    try:
        farmer = (
            db.query(Farmer)
            .join(User)
            .filter(User.phone_number == "9876543210")
            .first()
        )
        if not farmer:
            print("[!] Demo farmer not found. Please run seed_demo_data.py first.")
            sys.exit(1)

        commodity = (
            db.query(Commodity)
            .filter(Commodity.commodity_code == "PADDY")
            .first()
        )
        today = date.today()

        print(f"[*] Starting API validation for Farmer '{farmer.full_name}' and Commodity '{commodity.name}'...")

        # 1. Create Procurement Request
        res1 = client.post(
            "/api/v1/procurement-requests",
            json={
                "farmer_id": str(farmer.id),
                "commodity_id": str(commodity.id),
                "requested_quantity": 25.0,
                "preferred_date": str(today),
                "longitude": 79.5500,
                "latitude": 16.8600,
            },
        )
        assert res1.status_code == 201, f"Create request failed: {res1.text}"
        req_data = res1.json()
        req_id = req_data["id"]
        print(f"[1] Created Procurement Request: {req_id} (Status: {req_data['status']})")

        # 2. Evaluate Eligibility
        res2 = client.get(f"/api/v1/procurement-requests/{req_id}/eligibility")
        assert res2.status_code == 200, f"Eligibility failed: {res2.text}"
        elig = res2.json()
        print(f"[2] Evaluated Eligibility: {len(elig['eligible_centres'])} centres eligible")
        assert len(elig["eligible_centres"]) >= 1

        # 3. Recommend Centres
        res3 = client.post(f"/api/v1/procurement-requests/{req_id}/recommendations")
        assert res3.status_code == 200, f"Recommendation failed: {res3.text}"
        rec = res3.json()
        rec_centre = rec["recommended_centre"]
        rec_centre_id = rec_centre["centre_id"]
        print(f"[3] Recommended Centre: {rec_centre['centre_name']} (Score: {rec_centre['score']:.4f})")

        # 4. Fetch Available Slots
        res4 = client.get(f"/api/v1/centres/{rec_centre_id}/slots?date={today}")
        assert res4.status_code == 200, f"Get slots failed: {res4.text}"
        slots_data = res4.json()
        target_slot = slots_data["slots"][0]
        print(f"[4] Fetched Centre Slots: {len(slots_data['slots'])} windows available (First window: {target_slot['start_time']} - {target_slot['end_time']})")

        # 5. Confirm Slot & Token Issuance
        res5 = client.post(
            f"/api/v1/procurement-requests/{req_id}/confirm-slot",
            json={
                "centre_id": rec_centre_id,
                "slot_id": target_slot["slot_id"],
            },
        )
        assert res5.status_code == 200, f"Confirm slot failed: {res5.text}"
        booking = res5.json()
        token_num = booking["token"]["token_number"]
        print(f"[5] Confirmed Slot! Request Status: {booking['status']}, Token Issued: {token_num}")

        # 6. Physical Gate Check-in
        res6 = client.post(
            f"/api/v1/centres/{rec_centre_id}/check-in",
            json={
                "token_number": token_num,
                "vehicle_number": "TS-08-AB-9999",
            },
        )
        assert res6.status_code == 200, f"Check-in failed: {res6.text}"
        checkin = res6.json()
        print(f"[6] Gate Check-in Successful! Queue Status: {checkin['status']}, Dynamic Position: {checkin['dynamic_position']}")

        # 7. View Centre Queue
        res7 = client.get(f"/api/v1/centres/{rec_centre_id}/queue?date={today}")
        assert res7.status_code == 200, f"View queue failed: {res7.text}"
        queue = res7.json()
        print(f"[7] Current Yard Queue: {queue['total_waiting']} waiting, {queue['total_called']} called, {queue['total_processing']} processing")

        # 8. Operator Call Next
        res8 = client.post(
            f"/api/v1/centres/{rec_centre_id}/queue/call-next",
            json={"counter_or_bay": "BAY-1"},
        )
        assert res8.status_code == 200, f"Call next failed: {res8.text}"
        called = res8.json()
        print(f"[8] Operator Called Next: Token {called['token_number']} summoned to {called['counter_or_bay']}")

        # 9. Update Status to PROCESSING
        res9 = client.post(
            f"/api/v1/centres/{rec_centre_id}/queue/{called['queue_entry_id']}/status",
            json={"status": "PROCESSING"},
        )
        assert res9.status_code == 200, f"Update status failed: {res9.text}"
        print(f"[9] Yard Status Advanced to: {res9.json()['status']}")

        print("\n[+] FULL END-TO-END WORKFLOW VERIFIED SUCCESSFULLY AGAINST SEEDED DEMO DATA!")
    finally:
        db.close()


if __name__ == "__main__":
    main()
