"""Proximity Agent — the specific compound-risk pattern this whole project is named
after: a hazardous permit (hot work, confined space entry) active in one zone while an
ADJACENT zone shows elevated gas readings. Neither the Permit Agent (only ever sees its
own zone's permits) nor the Gas Agent (only ever sees its own zone's readings) can catch
this alone — it only exists in the combination *across* a zone boundary. This is exactly
the failure mode behind this project's own seeded battery_3 incident ("two permits for
adjacent spaces were approved without cross-checking gas conditions between them") — this
agent is what would actually catch that pattern live, not just narrate it as history.

Adjacency comes from PlantConfig.compute_adjacency() (derived from real zone layout
geometry), not a separately hand-maintained list.
"""
from __future__ import annotations

HAZARD_WORK_TYPES = {"hot_work", "confined_space_entry"}


class ProximityAgent:
    def assess(
        self, zone_id: str, permit_out: dict, gas_by_zone: dict[str, dict],
        adjacency: dict[str, list[str]], zone_names: dict[str, str],
    ) -> dict:
        active_permit = permit_out.get("active_permit")
        if not active_permit or active_permit["work_type"] not in HAZARD_WORK_TYPES:
            return {"agent": "proximity", "score": 0.0, "details": []}

        worst = 0.0
        details = []
        for neighbor_id in adjacency.get(zone_id, []):
            neighbor_gas = gas_by_zone.get(neighbor_id)
            if not neighbor_gas or neighbor_gas["score"] <= 0:
                continue
            worst = max(worst, neighbor_gas["score"])
            neighbor_name = zone_names.get(neighbor_id, neighbor_id)
            elevated = ", ".join(neighbor_gas["details"]) or "elevated readings"
            details.append(
                f"{active_permit['work_type'].replace('_', ' ').title()} permit {active_permit['permit_id']} "
                f"active while adjacent zone {neighbor_name} shows {elevated}"
            )

        return {"agent": "proximity", "score": round(worst, 3), "details": details}
