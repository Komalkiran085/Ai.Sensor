from simulator.sensor_simulator import ZONES

# Thresholds per gas type
THRESHOLDS = {
    "co_ppm": {"warning": 35, "critical": 50, "extreme": 75},
    "h2s_ppm": {"warning": 5, "critical": 10, "extreme": 20},
    "methane_ppm": {"warning": 300, "critical": 450, "extreme": 600},
    "temperature": {"warning": 42, "critical": 50, "extreme": 60},
}

WORK_TYPE_RISK = {
    "confined_space_entry": 1.0,
    "hot_work": 0.9,
    "electrical_isolation": 0.6,
    "general_maintenance": 0.3,
    "inspection": 0.2,
}


def score_gas(reading: dict) -> dict:
    """Score a single zone's gas readings. Returns per-gas level and overall gas score 0-1."""
    scores = {}
    max_score = 0.0
    for gas, thresholds in THRESHOLDS.items():
        val = reading.get(gas, 0)
        if val >= thresholds["extreme"]:
            scores[gas] = {"level": "extreme", "value": val, "threshold": thresholds["extreme"], "score": 1.0}
        elif val >= thresholds["critical"]:
            scores[gas] = {"level": "critical", "value": val, "threshold": thresholds["critical"], "score": 0.8}
        elif val >= thresholds["warning"]:
            scores[gas] = {"level": "warning", "value": val, "threshold": thresholds["warning"], "score": 0.5}
        else:
            scores[gas] = {"level": "normal", "value": val, "threshold": thresholds["warning"], "score": 0.0}
        max_score = max(max_score, scores[gas]["score"])
    return {"gas_scores": scores, "overall_gas_score": max_score}


def compute_compound_risk(gas_result: dict, permits: list, shift: dict) -> dict:
    """Compute the compound risk score combining gas, permits, shift."""
    gas_score = gas_result["overall_gas_score"]

    # Permit factor
    permit_factor = 0.0
    active_permit = None
    for p in permits:
        wt = p.get("work_type", "general_maintenance")
        pf = WORK_TYPE_RISK.get(wt, 0.3)
        if pf > permit_factor:
            permit_factor = pf
            active_permit = p

    # Shift factor
    shift_factor = 0.0
    if shift.get("is_changeover"):
        shift_factor = 0.3
    elif shift.get("changeover_soon"):
        shift_factor = 0.15
    if shift.get("fatigue_risk"):
        shift_factor += 0.1

    # Compound score: weighted combination
    if gas_score == 0 and permit_factor == 0:
        compound = 0.0
    elif gas_score > 0 and permit_factor > 0:
        # Multiplicative boost when both gas AND permit risk present
        compound = min(1.0, gas_score * 0.5 + permit_factor * 0.3 + shift_factor + gas_score * permit_factor * 0.3)
    else:
        compound = gas_score * 0.6 + permit_factor * 0.2 + shift_factor

    # Determine severity
    if compound >= 0.8:
        severity = "extreme"
    elif compound >= 0.6:
        severity = "critical"
    elif compound >= 0.35:
        severity = "warning"
    else:
        severity = "normal"

    factors = []
    for gas, info in gas_result["gas_scores"].items():
        if info["score"] > 0:
            factors.append(f"{gas}: {info['value']} ({info['level']})")
    if active_permit:
        factors.append(f"Active permit: {active_permit['permit_id']} ({active_permit['work_type']})")
    if shift.get("changeover_soon"):
        factors.append(f"Shift changeover in {shift.get('minutes_remaining', '?')} min")
    if shift.get("fatigue_risk"):
        factors.append("Fatigue risk: >6hrs into shift")

    return {
        "compound_score": round(compound, 3),
        "severity": severity,
        "gas_score": gas_score,
        "permit_factor": permit_factor,
        "shift_factor": shift_factor,
        "active_permit": active_permit,
        "contributing_factors": factors,
    }
