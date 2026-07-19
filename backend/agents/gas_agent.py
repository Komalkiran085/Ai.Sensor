"""Gas Agent — scores current readings against this zone's configured thresholds, AND
estimates lead time from the recent trend. Catching "38 ppm but climbing fast" before it
crosses a line is the whole point of lead time being a first-class output, not an
afterthought (docs/SYSTEM_DESIGN.md §1)."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import SensorReading
from plant_config import ZoneConfig

TREND_WINDOW_MINUTES = 10
TREND_MIN_POINTS = 3


class GasAgent:
    async def assess(self, session: AsyncSession, zone: ZoneConfig, readings: list[dict]) -> dict:
        sensors_by_type = {s.type: s for s in zone.sensors}
        per_sensor: dict[str, dict] = {}
        details: list[str] = []
        max_score = 0.0
        lead_time_minutes: int | None = None

        for r in readings:
            sensor_cfg = sensors_by_type.get(r["sensor_type"])
            if sensor_cfg is None:
                continue
            value = r["value"]
            th = sensor_cfg.thresholds
            if value >= th.extreme:
                level, score = "extreme", 1.0
            elif value >= th.critical:
                level, score = "critical", 0.8
            elif value >= th.warning:
                level, score = "warning", 0.5
            else:
                level, score = "normal", 0.0

            per_sensor[r["sensor_type"]] = {"level": level, "value": value, "score": score}
            if score > 0:
                details.append(f"{r['sensor_type']}: {value}{sensor_cfg.unit} ({level})")
            max_score = max(max_score, score)

            trend_lead_time = await self._estimate_lead_time(session, sensor_cfg, value)
            if trend_lead_time is not None:
                if lead_time_minutes is None or trend_lead_time < lead_time_minutes:
                    lead_time_minutes = trend_lead_time

        return {
            "agent": "gas",
            "score": max_score,
            "details": details,
            "per_sensor": per_sensor,
            "lead_time_minutes": lead_time_minutes,
        }

    async def _estimate_lead_time(self, session: AsyncSession, sensor_cfg, current_value: float) -> int | None:
        th = sensor_cfg.thresholds
        if current_value < th.warning:
            next_threshold = th.warning
        elif current_value < th.critical:
            next_threshold = th.critical
        elif current_value < th.extreme:
            next_threshold = th.extreme
        else:
            return None  # already at/above extreme — nothing further to count down to

        since = datetime.now(timezone.utc) - timedelta(minutes=TREND_WINDOW_MINUTES)
        result = await session.execute(
            select(SensorReading.value, SensorReading.ts)
            .where(SensorReading.sensor_id == sensor_cfg.id, SensorReading.ts >= since)
            .order_by(SensorReading.ts.asc())
        )
        rows = result.all()
        if len(rows) < TREND_MIN_POINTS:
            return None

        t0 = rows[0][1]
        xs = [(ts - t0).total_seconds() / 60.0 for _, ts in rows]
        ys = [v for v, _ in rows]
        slope = _linear_slope(xs, ys)
        if slope <= 0:
            return None  # flat or falling — no impending crossing to report

        minutes_to_cross = (next_threshold - current_value) / slope
        return max(0, round(minutes_to_cross))


def _linear_slope(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den = sum((x - mean_x) ** 2 for x in xs)
    return num / den if den else 0.0
