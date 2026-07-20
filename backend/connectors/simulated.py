"""Simulated adapters — stand in for real SCADA/permit/shift systems during the pilot,
behind the exact same interfaces a real integration would use (connectors/base.py).
Swapping these for a real plant's systems later means writing a new adapter class,
not touching anything upstream.
"""
from __future__ import annotations
import random
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from connectors.base import SCADAAdapter, PermitAdapter, ShiftAdapter, WorkerLocationAdapter
from plant_config import PlantConfig, ZoneConfig, ShiftsConfig

# Realistic "quiet" ranges per sensor type, used to generate normal-looking noise.
BASELINES: dict[str, tuple[float, float]] = {
    "co_ppm": (5, 20),
    "h2s_ppm": (0.5, 3),
    "methane_ppm": (50, 200),
    "temperature": (28, 38),
}

SCENARIO_RAMP_SECONDS = 2


class SimulatedSCADAAdapter(SCADAAdapter):
    def __init__(self, zones: list[ZoneConfig]):
        self._zones: dict[str, ZoneConfig] = {z.id: z for z in zones}
        self._scenario_zone: str | None = None
        self._scenario_start: float = 0.0

    async def get_readings(self) -> dict[str, list[dict]]:
        now = time.time()
        in_scenario = self._scenario_zone is not None
        elapsed = (now - self._scenario_start) if in_scenario else 0.0
        progress = min(elapsed / SCENARIO_RAMP_SECONDS, 1.0)

        readings: dict[str, list[dict]] = {}
        for zone_id, zone in self._zones.items():
            zone_readings = []
            ramping = in_scenario and zone_id == self._scenario_zone
            for sensor in zone.sensors:
                lo, hi = BASELINES.get(sensor.type, (0, 10))
                if ramping:
                    # Ramp toward just past this sensor's own "extreme" threshold — generic
                    # to whatever thresholds this plant's config declares, not hardcoded.
                    target = sensor.thresholds.extreme * 1.1
                    value = lo + progress * (target - lo)
                else:
                    value = random.uniform(lo, hi)
                zone_readings.append({
                    "sensor_id": sensor.id,
                    "sensor_type": sensor.type,
                    "value": round(value, 1),
                })
            readings[zone_id] = zone_readings
        return readings

    def trigger_scenario(self, zone_id: str) -> None:
        """Demo-only: ramps every sensor in a zone toward its extreme threshold over
        a couple of seconds, so a compound-risk scenario (e.g. Vizag-style gas buildup)
        shows up on the very next orchestrator tick instead of making the demo wait."""
        self._scenario_zone = zone_id
        self._scenario_start = time.time()

    def reset_scenario(self) -> None:
        self._scenario_zone = None
        self._scenario_start = 0.0


class SimulatedPermitAdapter(PermitAdapter):
    """Seeded with a few representative permits so the pilot zone (and a couple of
    others) has something for the Permit Agent to reason about out of the box."""

    def __init__(self, zones: list[ZoneConfig]):
        now = datetime.now(timezone.utc)
        seed_by_zone = {
            "battery_3": ("confined_space_entry", "high"),
            "blast_furnace_1": ("hot_work", "high"),
            "workshop_b": ("electrical_isolation", "medium"),
        }
        self._permits: list[dict] = []
        counter = 2094
        worker_names = ["Rajesh Kumar", "Sneha Patel", "Vikram Singh"]
        for idx, zone in enumerate(zones):
            seed = seed_by_zone.get(zone.id)
            if not seed:
                continue
            work_type, risk_class = seed
            self._permits.append({
                "permit_id": f"PTW-{counter}",
                "zone_id": zone.id,
                "worker_name": worker_names[idx % len(worker_names)],
                "work_type": work_type,
                "risk_class": risk_class,
                "status": "active",
                "start_time": now.isoformat(),
                "end_time": now.isoformat(),
            })
            counter += 1

    async def get_permits_for_zone(self, zone_id: str) -> list[dict]:
        return [p for p in self._permits if p["zone_id"] == zone_id and p["status"] == "active"]

    async def get_active_permits(self) -> list[dict]:
        return [p for p in self._permits if p["status"] == "active"]

    async def suspend_permit(self, permit_id: str) -> bool:
        for p in self._permits:
            if p["permit_id"] == permit_id:
                p["status"] = "suspended"
                return True
        return False

    def reset(self) -> list[str]:
        """Restores every permit to active. Returns the ids that were actually
        suspended, so the caller can put the database back in sync too."""
        reactivated = [p["permit_id"] for p in self._permits if p["status"] != "active"]
        for p in self._permits:
            p["status"] = "active"
        return reactivated


class SimulatedShiftAdapter(ShiftAdapter):
    def __init__(self, shifts: ShiftsConfig, plant_timezone: str = "UTC"):
        self._shifts = shifts.pattern
        self._changeover_minutes = shifts.changeover_window_minutes
        self._fatigue_after_minutes = shifts.fatigue_after_hours * 60
        self._tz = ZoneInfo(plant_timezone)

    def get_current_shift(self) -> dict:
        now = datetime.now(timezone.utc).astimezone(self._tz)
        minute_of_day = now.hour * 60 + now.minute
        for s in self._shifts:
            start_min = s.start.hour * 60 + s.start.minute
            end_min = s.end.hour * 60 + s.end.minute
            spans_midnight = end_min <= start_min
            in_shift = (
                (minute_of_day >= start_min or minute_of_day < end_min)
                if spans_midnight else
                (start_min <= minute_of_day < end_min)
            )
            if not in_shift:
                continue
            minutes_into = (minute_of_day - start_min) % (24 * 60)
            total_minutes = (end_min - start_min) % (24 * 60) or 24 * 60
            minutes_remaining = max(0, total_minutes - minutes_into)
            return {
                "shift_name": s.name,
                "minutes_remaining": minutes_remaining,
                "changeover_soon": minutes_remaining <= self._changeover_minutes,
                "is_changeover": minutes_remaining <= 5,
                "fatigue_risk": minutes_into > self._fatigue_after_minutes,
            }
        return {"shift_name": "Unknown", "minutes_remaining": 0, "changeover_soon": False,
                "is_changeover": False, "fatigue_risk": False}


class SimulatedWorkerLocationAdapter(WorkerLocationAdapter):
    """Zone-level presence, not (x, y) — see the interface docstring for why. Workers
    on an active permit are placed in that permit's zone; a couple of roving workers
    (safety officer, shift supervisor) cycle between zones on a timer, the way someone
    actually walking the floor would show up differently on each badge-in."""

    ROVING_CYCLE_SECONDS = 45

    def __init__(self, permits: PermitAdapter, zone_ids: list[str]):
        self._permits = permits
        self._zone_ids = zone_ids
        self._roving_workers = [
            {"worker_id": "EMP-9001", "name": "Priya Menon", "role": "Safety Officer"},
            {"worker_id": "EMP-9002", "name": "Arjun Nair", "role": "Shift Supervisor"},
        ]

    async def get_worker_locations(self) -> list[dict]:
        locations = []
        for p in await self._permits.get_active_permits():
            locations.append({
                "worker_id": p.get("worker_id") or p["permit_id"],
                "name": p.get("worker_name", "Worker"),
                "zone_id": p["zone_id"],
                "role": p["work_type"].replace("_", " ").title(),
            })

        if self._zone_ids:
            now = time.time()
            for i, worker in enumerate(self._roving_workers):
                idx = int(now / self.ROVING_CYCLE_SECONDS) + i * 2
                zone_id = self._zone_ids[idx % len(self._zone_ids)]
                locations.append({
                    "worker_id": worker["worker_id"],
                    "name": worker["name"],
                    "zone_id": zone_id,
                    "role": worker["role"],
                })
        return locations
