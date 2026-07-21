"""Coordinator Agent — the only piece that sees every specialist's output at once and
reasons about the combination. This is what makes "compound risk detection" real instead
of one scoring function: each specialist below only ever sees its own slice of the data.
"""
from __future__ import annotations


def combine(
    gas: dict, permit: dict, shift: dict, compliance: dict | None = None, incident: dict | None = None,
    equipment: dict | None = None, proximity: dict | None = None,
) -> dict:
    gas_score = gas["score"]
    permit_score = permit["score"]
    shift_score = shift["score"]
    equipment_score = equipment["score"] if equipment else 0.0

    if gas_score == 0 and permit_score == 0:
        compound = 0.0
    elif gas_score > 0 and permit_score > 0:
        # Multiplicative boost when both gas AND permit risk are present at once —
        # this is the actual "compound" in compound risk.
        compound = min(1.0, gas_score * 0.5 + permit_score * 0.3 + shift_score + equipment_score + gas_score * permit_score * 0.3)
    else:
        compound = gas_score * 0.6 + permit_score * 0.2 + shift_score + equipment_score

    if compliance and compliance.get("score"):
        compound = min(1.0, compound + compliance["score"] * 0.1)

    # A close match to real past history is itself evidence, the same reasoning as the
    # compliance nudge above — weighted so it can move the needle but never manufacture
    # an alert on its own (the gas==0 and permit==0 branch above already forced 0.0).
    if incident and incident.get("score"):
        compound = min(1.0, compound + incident["score"] * 0.1)

    # A hazardous permit next to an already-elevated adjacent zone is a stronger,
    # more specific signal than the compliance/incident nudges above — this is the
    # exact cross-zone pattern the Digital Permit Intelligence capability is named for
    # (and this project's own seeded battery_3 incident's actual root cause), so it
    # carries a heavier weight. Still can't fire on its own: it requires an active
    # hazardous permit in THIS zone, which already means permit_score > 0 above.
    if proximity and proximity.get("score"):
        compound = min(1.0, compound + proximity["score"] * 0.25)

    if compound >= 0.8:
        severity = "extreme"
    elif compound >= 0.6:
        severity = "critical"
    elif compound >= 0.35:
        severity = "warning"
    else:
        severity = "normal"

    contributing_factors = list(gas["details"]) + list(permit["details"]) + list(shift["details"])
    if equipment:
        contributing_factors += list(equipment["details"])
    if compliance:
        contributing_factors += list(compliance["details"])
    if incident and incident.get("matches"):
        # Vector search always returns a "closest" result even when nothing is truly
        # similar, so gate on score there; a keyword-fallback hit is a real substring
        # match on its own (no ranking to gate by), so it always surfaces.
        is_vector = incident.get("retrieval") == "vector"
        if not is_vector or incident.get("score"):
            closest = incident["matches"][0]
            label = "incident" if closest["type"] == "incident" else "near-miss"
            contributing_factors.append(
                f"Similar past {label} ({closest.get('date', 'undated')}, {closest['zone_id']}): "
                f"{closest['description'][:100]}…"
            )
    if proximity:
        contributing_factors += list(proximity["details"])

    return {
        "compound_score": round(compound, 3),
        "severity": severity,
        "lead_time_minutes": gas.get("lead_time_minutes"),
        "contributing_factors": contributing_factors,
        "agent_outputs": {
            "gas": gas,
            "permit": permit,
            "shift": shift,
            "compliance": compliance,
            "incident": incident,
            "equipment": equipment,
            "proximity": proximity,
        },
    }


def compliance_query_text(gas: dict, permit: dict) -> str:
    """What should the Compliance Agent look up, given what the other agents found?
    A natural-language description reads far better for semantic vector search than a
    bag of keywords — this is the sentence that gets embedded and compared against
    each regulation clause's own embedding."""
    parts: list[str] = []
    active_permit = permit.get("active_permit")
    if active_permit:
        parts.append(f"{active_permit['work_type'].replace('_', ' ')} permit")

    elevated = [
        gas_type.replace("_ppm", "").replace("_", " ")
        for gas_type, info in gas.get("per_sensor", {}).items()
        if info["score"] > 0
    ]
    if elevated:
        parts.append("elevated " + " and ".join(elevated) + " readings")

    if not parts:
        return ""
    return "Safety conditions: " + ", ".join(parts) + "."
