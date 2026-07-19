"""Automation policy — decides whether a state-changing action (suspend a permit,
trigger evacuation) can fire automatically or needs one human click first.

Default: `normal`/`warning` never propose state-changing actions at all (only a
dashboard flag + notification). `critical` and `extreme` do propose them, and both
require human confirmation by default. A hazard type can override the cutoff to be
stricter (e.g. requiring confirmation starting at `warning`) via plant.config.yaml's
automation.overrides — see docs/SYSTEM_DESIGN.md §1.
"""
from __future__ import annotations

from plant_config import AutomationConfig

_SEVERITY_ORDER = ["normal", "warning", "critical", "extreme"]
_DEFAULT_CUTOFF = "critical"


def requires_confirmation(severity: str, hazard_type: str | None, automation_cfg: AutomationConfig) -> bool:
    cutoff = _DEFAULT_CUTOFF
    if hazard_type and hazard_type in automation_cfg.overrides:
        cutoff = automation_cfg.overrides[hazard_type].human_confirm_from
    return _SEVERITY_ORDER.index(severity) >= _SEVERITY_ORDER.index(cutoff)


def proposes_action(severity: str) -> bool:
    """Only critical/extreme ever propose a state-changing action in the first place."""
    return _SEVERITY_ORDER.index(severity) >= _SEVERITY_ORDER.index("critical")
