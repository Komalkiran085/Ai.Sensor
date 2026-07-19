"""Loads plant.config.yaml into the database — idempotent, safe to run on every startup.

This is the mechanism behind "install to a new plant = fill in a config file, not write
code" (docs/SYSTEM_DESIGN.md §3.1): zones/equipment/sensors/cameras are declared in YAML,
and this function makes the database match that declaration every time the app boots.
"""
from __future__ import annotations
import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from db.database import async_session, init_db
from db.models import Zone, Equipment, Sensor, Camera
from plant_config import PlantConfig, load_plant_config

logger = logging.getLogger(__name__)


async def sync_plant_config(session: AsyncSession, cfg: PlantConfig) -> None:
    for zone_cfg in cfg.zones:
        zone = await session.get(Zone, zone_cfg.id)
        if zone is None:
            zone = Zone(id=zone_cfg.id)
            session.add(zone)
        zone.name = zone_cfg.name
        zone.hazard_classification = zone_cfg.hazard_classification
        zone.boundary = zone_cfg.boundary

        for eq_cfg in zone_cfg.equipment:
            eq = await session.get(Equipment, eq_cfg.id)
            if eq is None:
                eq = Equipment(id=eq_cfg.id)
                session.add(eq)
            eq.zone_id = zone_cfg.id
            eq.type = eq_cfg.type
            eq.install_date = eq_cfg.install_date

        for sensor_cfg in zone_cfg.sensors:
            sensor = await session.get(Sensor, sensor_cfg.id)
            if sensor is None:
                sensor = Sensor(id=sensor_cfg.id)
                session.add(sensor)
            sensor.zone_id = zone_cfg.id
            sensor.sensor_type = sensor_cfg.type
            sensor.unit = sensor_cfg.unit
            sensor.warning_threshold = sensor_cfg.thresholds.warning
            sensor.critical_threshold = sensor_cfg.thresholds.critical
            sensor.extreme_threshold = sensor_cfg.thresholds.extreme
            sensor.calibration_date = sensor_cfg.calibration_date

        for cam_cfg in zone_cfg.cameras:
            cam = await session.get(Camera, cam_cfg.id)
            if cam is None:
                cam = Camera(id=cam_cfg.id)
                session.add(cam)
            cam.zone_id = zone_cfg.id
            cam.stream_url = cam_cfg.stream_url

    await session.commit()
    logger.info("plant.config.yaml synced: %d zones", len(cfg.zones))


async def bootstrap() -> PlantConfig:
    settings = get_settings()
    cfg = load_plant_config(settings.PLANT_CONFIG_PATH)
    async with async_session() as session:
        await sync_plant_config(session, cfg)
    return cfg


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    async def _main():
        await init_db()
        await bootstrap()

    asyncio.run(_main())
