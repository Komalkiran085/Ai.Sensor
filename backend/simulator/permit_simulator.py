from datetime import datetime, timezone, timedelta
from typing import Dict, List
from db.models import PermitStatus


DEMO_PERMITS = [
    {
        "permit_id": "PTW-2094",
        "worker_name": "Raju Kumar",
        "worker_id": "EMP-1147",
        "zone": "BATTERY_3",
        "work_type": "confined_space_entry",
        "risk_class": "high",
        "status": PermitStatus.ACTIVE,
    },
    {
        "permit_id": "PTW-2095",
        "worker_name": "Amit Singh",
        "worker_id": "EMP-0832",
        "zone": "BLAST_FURNACE_1",
        "work_type": "hot_work",
        "risk_class": "high",
        "status": PermitStatus.ACTIVE,
    },
    {
        "permit_id": "PTW-2096",
        "worker_name": "Priya Devi",
        "worker_id": "EMP-0456",
        "zone": "WORKSHOP_B",
        "work_type": "electrical_isolation",
        "risk_class": "medium",
        "status": PermitStatus.ACTIVE,
    },
]


class PermitSimulator:
    def __init__(self):
        now = datetime.now(timezone.utc)
        self.permits: List[dict] = []
        for p in DEMO_PERMITS:
            permit = dict(p)
            permit["start_time"] = (now - timedelta(minutes=30)).isoformat()
            permit["end_time"] = (now + timedelta(hours=4)).isoformat()
            permit["status"] = permit["status"].value
            self.permits.append(permit)

    def get_active_permits(self) -> List[dict]:
        return [p for p in self.permits if p["status"] == "active"]

    def get_permits_for_zone(self, zone: str) -> List[dict]:
        return [p for p in self.permits if p["zone"] == zone and p["status"] == "active"]

    def suspend_permit(self, permit_id: str) -> bool:
        for p in self.permits:
            if p["permit_id"] == permit_id:
                p["status"] = "suspended"
                return True
        return False

    def reset(self):
        """Reset all permits to active state."""
        now = datetime.now(timezone.utc)
        self.permits = []
        for p in DEMO_PERMITS:
            permit = dict(p)
            permit["start_time"] = (now - timedelta(minutes=30)).isoformat()
            permit["end_time"] = (now + timedelta(hours=4)).isoformat()
            permit["status"] = permit["status"].value
            self.permits.append(permit)

    def add_permit(self, permit: dict):
        self.permits.append(permit)
