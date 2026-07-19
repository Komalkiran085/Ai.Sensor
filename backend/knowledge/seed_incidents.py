"""Seed incident and near-miss records — illustrative examples representing the kind
of history a real plant would have accumulated, not verified real events. In a real
deployment this table would be populated from the plant's actual incident management
system; the point here is to demonstrate the retrieval mechanism against realistic
data, the same way seed_regulations.py does for the Compliance Agent.
"""

INCIDENTS: list[dict] = [
    {
        "zone_id": "battery_3",
        "incident_date": "2024-11-18",
        "description": (
            "Worker began confined space entry in the coke oven battery access chamber while "
            "a hot work permit was simultaneously active in the adjacent flue. CO levels rose "
            "during the entry and the worker was evacuated with mild symptoms before further harm."
        ),
        "severity": "critical",
        "contributing_factors": ["confined_space_entry", "hot_work", "gas_buildup"],
        "root_cause": "Two permits for adjacent spaces were approved without cross-checking gas conditions between them.",
    },
    {
        "zone_id": "blast_furnace_1",
        "incident_date": "2023-06-02",
        "description": (
            "Hot work was carried out near the furnace charging area during a period of elevated "
            "flammable gas readings that had not been flagged to the permit issuer. No ignition "
            "occurred, but post-incident review found the gas data existed and was not connected "
            "to the permit approval."
        ),
        "severity": "extreme",
        "contributing_factors": ["hot_work", "gas_buildup", "permit_process_gap"],
        "root_cause": "Gas monitoring data and permit issuance were on separate systems with no automated cross-check.",
    },
    {
        "zone_id": "workshop_b",
        "incident_date": "2025-02-09",
        "description": (
            "Electrical isolation work was performed at shift changeover; the incoming shift was "
            "not briefed on the isolation in progress and a worker attempted to re-energize the "
            "circuit before work was complete."
        ),
        "severity": "critical",
        "contributing_factors": ["electrical_isolation", "shift_changeover"],
        "root_cause": "No formal handover checklist covering in-progress isolations at shift boundaries.",
    },
]

NEAR_MISSES: list[dict] = [
    {
        "zone_id": "battery_3",
        "report_date": "2025-08-04",
        "description": (
            "Gas detector in the battery access chamber showed a brief spike into the warning "
            "range while a confined space permit was active; the worker exited before levels "
            "climbed further. No injury."
        ),
        "reported_by": "Shift Supervisor",
    },
    {
        "zone_id": "storage_tank_a",
        "report_date": "2025-03-22",
        "description": (
            "A hot work request near the chemical storage tank farm was submitted without a "
            "prior gas clearance check; the permit officer caught the omission manually before "
            "work began."
        ),
        "reported_by": "Permit Officer",
    },
    {
        "zone_id": "blast_furnace_1",
        "report_date": "2026-01-15",
        "description": (
            "Two work permits were briefly active in the same furnace zone at once — a hot work "
            "permit and a general maintenance permit — before the overlap was noticed and one "
            "was paused."
        ),
        "reported_by": "Safety Officer",
    },
    {
        "zone_id": "workshop_b",
        "report_date": "2025-11-30",
        "description": (
            "Worker reported fatigue near the end of a long shift while performing electrical "
            "isolation; a second worker was brought in to complete the task rather than continue solo."
        ),
        "reported_by": "Worker self-report",
    },
]
