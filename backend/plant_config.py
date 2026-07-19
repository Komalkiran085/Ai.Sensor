"""Typed schema + loader for plant.config.yaml — the one file that captures everything
different about a given plant install (zones, sensors, connectors, agents, automation
overrides). Everything else in the app is identical across installs; this is what changes.
"""
from __future__ import annotations
from datetime import date, time
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class PlantIdentity(BaseModel):
    name: str
    location: str
    timezone: str = "UTC"


class ShiftPatternEntry(BaseModel):
    name: str
    start: time
    end: time


class ShiftsConfig(BaseModel):
    pattern: list[ShiftPatternEntry]
    changeover_window_minutes: int = 15
    fatigue_after_hours: int = 6


class SensorThresholds(BaseModel):
    warning: float
    critical: float
    extreme: float


class SensorConfig(BaseModel):
    id: str
    type: str
    unit: str = ""
    thresholds: SensorThresholds
    calibration_date: date | None = None


class EquipmentConfig(BaseModel):
    id: str
    type: str
    install_date: date | None = None


class CameraConfig(BaseModel):
    id: str
    stream_url: str


class ZoneConfig(BaseModel):
    id: str
    name: str
    hazard_classification: Literal["low", "medium", "high"]
    boundary: list[list[float]] = Field(default_factory=list)
    equipment: list[EquipmentConfig] = Field(default_factory=list)
    sensors: list[SensorConfig] = Field(default_factory=list)
    cameras: list[CameraConfig] = Field(default_factory=list)


class ConnectorConfig(BaseModel):
    adapter: str
    endpoint: str = ""


class ConnectorsConfig(BaseModel):
    scada: ConnectorConfig
    permit_system: ConnectorConfig
    shift_roster: ConnectorConfig
    worker_location: ConnectorConfig = ConnectorConfig(adapter="simulated")


class AgentsConfig(BaseModel):
    gas_agent: bool = True
    permit_agent: bool = True
    shift_agent: bool = True
    vision_agent: bool = False
    compliance_agent: bool = True
    incident_agent: bool = True


class AutomationOverride(BaseModel):
    human_confirm_from: Literal["warning", "critical", "extreme"]


class AutomationConfig(BaseModel):
    overrides: dict[str, AutomationOverride] = Field(default_factory=dict)


class DemoScenario(BaseModel):
    """A named, pre-built scenario for training/demo/tabletop-drill purposes — e.g.
    replaying the conditions behind a real past incident in a specific zone. Config-driven
    like everything else here: a different plant install can define its own named
    scenarios pointing at its own zones, not just this one."""
    id: str
    label: str
    zone_id: str
    description: str = ""


class PlantConfig(BaseModel):
    plant: PlantIdentity
    regulation_pack: str
    shifts: ShiftsConfig
    zones: list[ZoneConfig]
    connectors: ConnectorsConfig
    agents: AgentsConfig = AgentsConfig()
    automation: AutomationConfig = AutomationConfig()
    demo_scenarios: list[DemoScenario] = Field(default_factory=list)

    def zone(self, zone_id: str) -> ZoneConfig | None:
        return next((z for z in self.zones if z.id == zone_id), None)


def load_plant_config(path: str | Path = "plant.config.yaml") -> PlantConfig:
    text = Path(path).read_text()
    raw = yaml.safe_load(text)
    return PlantConfig.model_validate(raw)
