from __future__ import annotations
import asyncio
import random
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

ZONES = {
    "BATTERY_3": {"sensors": ["S-47", "S-48"], "risk_class": "high", "label": "Coke Oven Battery 3"},
    "CONTROL_ROOM": {"sensors": ["S-12"], "risk_class": "low", "label": "Main Control Room"},
    "STORAGE_TANK_A": {"sensors": ["S-23", "S-24"], "risk_class": "high", "label": "Chemical Storage A"},
    "WORKSHOP_B": {"sensors": ["S-31", "S-32"], "risk_class": "medium", "label": "Maintenance Workshop B"},
    "BLAST_FURNACE_1": {"sensors": ["S-55", "S-56", "S-57"], "risk_class": "high", "label": "Blast Furnace 1"},
    "UTILITY_AREA": {"sensors": ["S-70"], "risk_class": "low", "label": "Utility & Services"},
}

# Normal baseline ranges
BASELINES = {
    "co_ppm": (5, 20),
    "h2s_ppm": (0.5, 3),
    "methane_ppm": (50, 200),
    "temperature": (28, 38),
    "humidity": (40, 65),
}


class SensorSimulator:
    def __init__(self):
        self.readings: Dict[str, dict] = {}
        self.scenario_active = False
        self.scenario_start: float = 0
        self.scenario_zone: str = ""
        self._running = False

    def get_current_readings(self) -> Dict[str, dict]:
        return dict(self.readings)

    def get_zone_reading(self, zone: str) -> dict | None:
        return self.readings.get(zone)

    def trigger_vizag_scenario(self):
        self.scenario_active = True
        self.scenario_start = time.time()
        self.scenario_zone = "BATTERY_3"

    def reset_scenario(self):
        self.scenario_active = False
        self.scenario_start = 0
        self.scenario_zone = ""

    def _generate_normal(self, zone: str) -> dict:
        return {
            "zone": zone,
            "co_ppm": round(random.uniform(*BASELINES["co_ppm"]), 1),
            "h2s_ppm": round(random.uniform(*BASELINES["h2s_ppm"]), 1),
            "methane_ppm": round(random.uniform(*BASELINES["methane_ppm"]), 1),
            "temperature": round(random.uniform(*BASELINES["temperature"]), 1),
            "humidity": round(random.uniform(*BASELINES["humidity"]), 1),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sensors": ZONES[zone]["sensors"],
        }

    def _generate_scenario(self, zone: str, elapsed: float) -> dict:
        reading = self._generate_normal(zone)
        if zone == self.scenario_zone and self.scenario_active:
            progress = min(elapsed / 180, 1.0)  # 3-minute ramp
            reading["co_ppm"] = round(15 + progress * 55, 1)       # 15 → 70 ppm
            reading["h2s_ppm"] = round(2 + progress * 12, 1)       # 2 → 14 ppm
            reading["methane_ppm"] = round(150 + progress * 350, 1) # 150 → 500 ppm
            reading["temperature"] = round(32 + progress * 18, 1)  # 32 → 50°C
        return reading

    async def run(self):
        self._running = True
        while self._running:
            for zone in ZONES:
                if self.scenario_active:
                    elapsed = time.time() - self.scenario_start
                    self.readings[zone] = self._generate_scenario(zone, elapsed)
                else:
                    self.readings[zone] = self._generate_normal(zone)
            await asyncio.sleep(3)

    def stop(self):
        self._running = False
