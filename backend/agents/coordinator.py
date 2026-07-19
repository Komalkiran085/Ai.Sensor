"""Coordinator Agent — the only piece that sees every specialist's output at once and
reasons about the combination. This is what makes "compound risk detection" real instead
of one scoring function: each specialist below only ever sees its own slice of the data.
"""
from __future__ import annotations


def combine(gas: dict, permit: dict, shift: dict, compliance: dict | None = None, incident: dict | None = None) -> dict:
    gas_score = gas["score"]
    permit_score = permit["score"]
    shift_score = shift["score"]

    if gas_score == 0 and permit_score == 0:
        compound = 0.0
    elif gas_score > 0 and permit_score > 0:
        # Multiplicative boost when both gas AND permit risk are present at once —
        # this is the actual "compound" in compound risk.
        compound = min(1.0, gas_score * 0.5 + permit_score * 0.3 + shift_score + gas_score * permit_score * 0.3)
    else:
        compound = gas_score * 0.6 + permit_score * 0.2 + shift_score

    if compliance and compliance.get("score"):
        compound = min(1.0, compound + compliance["score"] * 0.1)

    if compound >= 0.8:
        severity = "extreme"
    elif compound >= 0.6:
        severity = "critical"
    elif compound >= 0.35:
        severity = "warning"
    else:
        severity = "normal"

    contributing_factors = list(gas["details"]) + list(permit["details"]) + list(shift["details"])
    if compliance:
        contributing_factors += list(compliance["details"])
    if incident and incident.get("matches"):
        closest = incident["matches"][0]
        label = "incident" if closest["type"] == "incident" else "near-miss"
        contributing_factors.append(
            f"Similar past {label} ({closest.get('date', 'undated')}, {closest['zone_id']}): "
            f"{closest['description'][:100]}…"
        )

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
