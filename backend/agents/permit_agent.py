"""Permit Agent — checks whether the work currently approved in a zone is inherently
risky, independent of what the sensors say. The Coordinator is what notices when this
combines with gas/shift signals into something worse than any one of them alone."""
from __future__ import annotations


class PermitAgent:
    WORK_TYPE_RISK = {
        "confined_space_entry": 1.0,
        "hot_work": 0.9,
        "electrical_isolation": 0.6,
        "general_maintenance": 0.3,
        "inspection": 0.2,
    }

    def assess(self, permits: list[dict]) -> dict:
        factor = 0.0
        active: dict | None = None
        for p in permits:
            pf = self.WORK_TYPE_RISK.get(p["work_type"], 0.3)
            if pf > factor:
                factor = pf
                active = p

        details = []
        if active:
            details.append(f"Active permit: {active['permit_id']} ({active['work_type'].replace('_', ' ')})")

        return {"agent": "permit", "score": factor, "details": details, "active_permit": active}
