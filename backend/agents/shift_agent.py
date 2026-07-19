"""Shift Agent — flags changeover windows and fatigue, because handoffs and long
stretches into a shift are when things get missed, independent of any single reading."""
from __future__ import annotations


class ShiftAgent:
    def assess(self, shift: dict) -> dict:
        factor = 0.0
        details = []

        if shift.get("is_changeover"):
            factor = 0.3
            details.append("Shift changeover in progress")
        elif shift.get("changeover_soon"):
            factor = 0.15
            details.append(f"Shift changeover in {shift.get('minutes_remaining', '?')} min")

        if shift.get("fatigue_risk"):
            factor += 0.1
            details.append("Fatigue risk: long into shift")

        return {"agent": "shift", "score": round(factor, 3), "details": details}
