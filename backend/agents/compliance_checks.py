"""Quality & Compliance Audit Agent — continuously checks real plant data against
regulatory rules, instead of a static illustrative list. Every check here reads from
an actual table (sensors, permits, equipment) or the live risk state; where no real
data source exists yet (fire system uptime, PPE compliance via CCTV, drill records),
the check is honestly reported as "unmonitored" rather than faked as a pass.
"""
from __future__ import annotations
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Equipment, Permit, Sensor
from plant_config import PlantConfig

CALIBRATION_INTERVAL_DAYS = 90


async def run_compliance_checks(session: AsyncSession, cfg: PlantConfig, zone_risks: dict) -> list[dict]:
    checks: list[dict] = []
    zone_names = {z.id: z.name for z in cfg.zones}

    checks += await _calibration_checks(session, zone_names)
    checks += await _permit_conflict_checks(session, zone_names)
    checks += await _permit_condition_checks(session, zone_names, zone_risks)
    checks += await _equipment_maintenance_checks(session, zone_names)
    checks += _unmonitored_checks()

    return checks


async def _calibration_checks(session: AsyncSession, zone_names: dict) -> list[dict]:
    result = await session.execute(select(Sensor))
    cutoff = date.today() - timedelta(days=CALIBRATION_INTERVAL_DAYS)
    checks = []
    for sensor in result.scalars().all():
        zone_label = zone_names.get(sensor.zone_id, sensor.zone_id)
        if sensor.calibration_date is None:
            checks.append({
                "rule": f"Gas detector calibration — {sensor.id} ({zone_label})",
                "ref": "OISD-RP-149", "status": "fail",
                "detail": "No calibration date on record.",
            })
        elif sensor.calibration_date < cutoff:
            days_overdue = (date.today() - sensor.calibration_date).days - CALIBRATION_INTERVAL_DAYS
            checks.append({
                "rule": f"Gas detector calibration — {sensor.id} ({zone_label})",
                "ref": "OISD-RP-149", "status": "fail",
                "detail": f"Last calibrated {sensor.calibration_date.isoformat()} — {days_overdue} days overdue.",
            })
        else:
            checks.append({
                "rule": f"Gas detector calibration — {sensor.id} ({zone_label})",
                "ref": "OISD-RP-149", "status": "pass",
                "detail": f"Last calibrated {sensor.calibration_date.isoformat()}.",
            })
    return checks


async def _permit_conflict_checks(session: AsyncSession, zone_names: dict) -> list[dict]:
    result = await session.execute(select(Permit).where(Permit.status == "active"))
    by_zone: dict[str, list[Permit]] = {}
    for p in result.scalars().all():
        by_zone.setdefault(p.zone_id, []).append(p)

    checks = []
    for zone_id, permits in by_zone.items():
        zone_label = zone_names.get(zone_id, zone_id)
        if len(permits) >= 2:
            work_types = ", ".join(p.work_type.replace("_", " ") for p in permits)
            checks.append({
                "rule": f"Simultaneous permit conflict check — {zone_label}",
                "ref": "OISD-GDN-237", "status": "fail",
                "detail": f"{len(permits)} active permits at once: {work_types}.",
            })
        else:
            checks.append({
                "rule": f"Simultaneous permit conflict check — {zone_label}",
                "ref": "OISD-GDN-237", "status": "pass",
                "detail": "Only one active permit in this zone.",
            })
    return checks


async def _permit_condition_checks(session: AsyncSession, zone_names: dict, zone_risks: dict) -> list[dict]:
    result = await session.execute(select(Permit).where(Permit.status == "active"))
    checks = []
    for p in result.scalars().all():
        zone_label = zone_names.get(p.zone_id, p.zone_id)
        gas = zone_risks.get(p.zone_id, {}).get("risk", {}).get("agent_outputs", {}).get("gas", {})
        elevated = [
            f"{gas_type}={info['value']} ({info['level']})"
            for gas_type, info in gas.get("per_sensor", {}).items()
            if info.get("score", 0) > 0
        ]

        if p.work_type == "confined_space_entry":
            rule, ref = "Gas clearance before confined space entry", "OISD-GDN-237"
        elif p.work_type == "hot_work":
            rule, ref = "Hot work permit proximity check", "Factory Act Sec 7A"
        else:
            continue

        if elevated:
            checks.append({
                "rule": f"{rule} — {p.permit_id} ({zone_label})",
                "ref": ref, "status": "fail",
                "detail": f"Active during elevated readings: {', '.join(elevated)}.",
            })
        else:
            checks.append({
                "rule": f"{rule} — {p.permit_id} ({zone_label})",
                "ref": ref, "status": "pass",
                "detail": "Gas readings normal for the duration of this permit's current tick.",
            })
    return checks


async def _equipment_maintenance_checks(session: AsyncSession, zone_names: dict) -> list[dict]:
    result = await session.execute(select(Equipment))
    checks = []
    for eq in result.scalars().all():
        zone_label = zone_names.get(eq.zone_id, eq.zone_id)
        if eq.maintenance_status != "operational":
            checks.append({
                "rule": f"Equipment maintenance status — {eq.id} ({zone_label})",
                "ref": "Internal QMS", "status": "fail",
                "detail": f"Status: {eq.maintenance_status}.",
            })
        else:
            checks.append({
                "rule": f"Equipment maintenance status — {eq.id} ({zone_label})",
                "ref": "Internal QMS", "status": "pass",
                "detail": "Operational.",
            })
    return checks


def _unmonitored_checks() -> list[dict]:
    """Rules the problem statement names but this system has no real data source for
    yet — reported honestly as unmonitored rather than faked as passing."""
    return [
        {
            "rule": "Shift handover safety briefing", "ref": "DGMS Circular 2023",
            "status": "unmonitored", "detail": "No briefing-log data source configured.",
        },
        {
            "rule": "Emergency evacuation drill (monthly)", "ref": "OISD-STD-116",
            "status": "unmonitored", "detail": "No drill-record data source configured.",
        },
        {
            "rule": "Fire detection system operational", "ref": "OISD-STD-189",
            "status": "unmonitored", "detail": "No fire-system telemetry integrated yet.",
        },
        {
            "rule": "PPE compliance in hazardous zones", "ref": "Factory Act Sec 35",
            "status": "unmonitored", "detail": "Requires CCTV/computer vision — not yet integrated.",
        },
    ]
