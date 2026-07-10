from __future__ import annotations
import asyncio
import logging
from intelligence.risk_engine import score_gas, compute_compound_risk
from ai.alert_generator import generate_alert_explanation, generate_incident_report
from simulator.sensor_simulator import SensorSimulator
from simulator.permit_simulator import PermitSimulator
from simulator.shift_simulator import ShiftSimulator
from ws.manager import manager

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, sensors: SensorSimulator, permits: PermitSimulator, shifts: ShiftSimulator):
        self.sensors = sensors
        self.permits = permits
        self.shifts = shifts
        self.alerts: list = []
        self.zone_risks: dict = {}
        self._running = False

    async def run(self):
        self._running = True
        logger.info("Orchestrator started")
        while self._running:
            await self._tick()
            await asyncio.sleep(5)

    async def _tick(self):
        readings = self.sensors.get_current_readings()
        shift = self.shifts.get_current_shift()

        for zone, reading in readings.items():
            gas_result = score_gas(reading)
            permits = self.permits.get_permits_for_zone(zone)
            risk = compute_compound_risk(gas_result, permits, shift)

            self.zone_risks[zone] = {
                "zone": zone,
                "reading": reading,
                "risk": risk,
                "shift": shift,
                "permits": permits,
            }

            # Broadcast sensor data
            await manager.broadcast("sensor_update", {"zone": zone, **reading, "risk": risk})

            # Fire alert if severity > normal
            if risk["severity"] in ("warning", "critical", "extreme"):
                alert = await self._create_alert(zone, risk, reading)
                if alert:
                    await manager.broadcast("alert", alert)

        # Broadcast full zone risk map
        await manager.broadcast("zone_risks", self.zone_risks)

    async def _create_alert(self, zone: str, risk: dict, reading: dict) -> dict | None:
        # Debounce: don't spam same zone within 30s
        for a in self.alerts[-10:]:
            if a["zone"] == zone and a.get("severity") == risk["severity"]:
                return None

        explanation = await generate_alert_explanation(zone, risk, reading)

        alert = {
            "id": len(self.alerts) + 1,
            "zone": zone,
            "severity": risk["severity"],
            "compound_score": risk["compound_score"],
            "explanation": explanation,
            "contributing_factors": risk["contributing_factors"],
            "permit": risk.get("active_permit"),
            "reading": reading,
        }
        self.alerts.append(alert)
        logger.warning(f"ALERT [{risk['severity'].upper()}] Zone {zone} — Score {risk['compound_score']}")
        return alert

    async def generate_report(self, zone: str) -> str:
        data = self.zone_risks.get(zone)
        if not data:
            return "No data available for this zone."
        alert_text = self.alerts[-1]["explanation"] if self.alerts else ""
        return await generate_incident_report(zone, data["risk"], data["reading"], alert_text)

    def get_all_alerts(self) -> list:
        return list(self.alerts)

    def get_zone_risks(self) -> dict:
        return dict(self.zone_risks)

    def stop(self):
        self._running = False
