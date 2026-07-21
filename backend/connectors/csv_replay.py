"""Replays a plant's own historical sensor export instead of scripted demo data.
Uploaded via POST /api/datasource/csv — the file lives only in process memory, no
disk write, since this is playback data, not something the app needs to persist.
"""
from __future__ import annotations
import csv
import io
import time

from connectors.base import SCADAAdapter
from plant_config import ZoneConfig

REQUIRED_COLUMNS = {"timestamp", "zone_id", "sensor_id", "sensor_type", "value"}
REPLAY_STEP_SECONDS = 5  # matches the orchestrator's own tick interval


class CSVFormatError(ValueError):
    """Raised on a malformed or unrecognized upload — carries a message safe to show
    the user directly (which column/value was the problem)."""


def parse_csv_steps(raw: bytes, zones: list[ZoneConfig]) -> list[dict[str, list[dict]]]:
    """Parses the upload into an ordered list of "steps" — each one a zone_id -> readings
    snapshot, in ascending timestamp order. Grouping by exact timestamp (rather than
    interpolating a shared clock) keeps this honest about only replaying what the file
    actually contains."""
    valid_zone_ids = {z.id for z in zones}
    valid_sensor_types = {s.type for z in zones for s in z.sensors}

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise CSVFormatError(f"File is not valid UTF-8 text: {e}") from e

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None or not REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        raise CSVFormatError(
            f"Missing required column(s): {', '.join(sorted(missing))}. "
            f"Expected columns: {', '.join(sorted(REQUIRED_COLUMNS))}"
        )

    rows_by_timestamp: dict[str, list[dict]] = {}
    seen_zone_ids: set[str] = set()
    seen_sensor_types: set[str] = set()

    for i, row in enumerate(reader, start=2):  # header is line 1
        zone_id = (row.get("zone_id") or "").strip()
        sensor_type = (row.get("sensor_type") or "").strip()
        seen_zone_ids.add(zone_id)
        seen_sensor_types.add(sensor_type)
        if zone_id not in valid_zone_ids:
            continue  # unknown zone — skip the row rather than fail the whole upload
        if sensor_type not in valid_sensor_types:
            continue  # unknown sensor type for this plant — same reasoning

        try:
            value = float(row["value"])
        except (TypeError, ValueError):
            raise CSVFormatError(f"Row {i}: '{row.get('value')}' is not a number in the value column.") from None

        ts = row["timestamp"].strip()
        rows_by_timestamp.setdefault(ts, []).append({
            "zone_id": zone_id,
            "sensor_id": (row.get("sensor_id") or f"{zone_id}-{sensor_type}").strip(),
            "sensor_type": sensor_type,
            "value": value,
        })

    if not rows_by_timestamp:
        raise CSVFormatError(
            f"No rows matched this plant's zones/sensor types. "
            f"File contained zone_id values {sorted(seen_zone_ids)} and sensor_type values "
            f"{sorted(seen_sensor_types)}; expected zone_id in {sorted(valid_zone_ids)} and "
            f"sensor_type in {sorted(valid_sensor_types)}."
        )

    steps: list[dict[str, list[dict]]] = []
    for ts in sorted(rows_by_timestamp):
        step: dict[str, list[dict]] = {}
        for r in rows_by_timestamp[ts]:
            step.setdefault(r["zone_id"], []).append({
                "sensor_id": r["sensor_id"], "sensor_type": r["sensor_type"], "value": r["value"],
            })
        steps.append(step)
    return steps


class CSVReplaySCADAAdapter(SCADAAdapter):
    """Advances one step per orchestrator tick and loops back to the start once the
    file is exhausted, so a demo can run indefinitely on a finite historical export.
    Zones the file has no data for fall back to a flat baseline reading per configured
    sensor, so the rest of the dashboard doesn't just go blank for them."""

    def __init__(self, steps: list[dict[str, list[dict]]], zones: list[ZoneConfig], filename: str):
        self._steps = steps
        self._zones = zones
        self.filename = filename
        self._start_time = time.time()

    @property
    def step_count(self) -> int:
        return len(self._steps)

    @property
    def current_step(self) -> int:
        # Derived from wall-clock elapsed time rather than a call counter, so reading
        # (GET /api/sensors, the status endpoint, etc.) never itself advances playback —
        # only time does, same as the simulated adapter's scenario ramp.
        return int((time.time() - self._start_time) / REPLAY_STEP_SECONDS)

    async def get_readings(self) -> dict[str, list[dict]]:
        step = self._steps[self.current_step % len(self._steps)]

        readings: dict[str, list[dict]] = {}
        for zone in self._zones:
            if zone.id in step:
                readings[zone.id] = step[zone.id]
            else:
                readings[zone.id] = [
                    {"sensor_id": s.id, "sensor_type": s.type, "value": round((s.thresholds.warning) * 0.4, 1)}
                    for s in zone.sensors
                ]
        return readings
