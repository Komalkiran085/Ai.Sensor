"""Resolves the `adapter:` name in plant.config.yaml's connectors section to an actual
adapter instance. Adding support for a new SCADA/permit/roster vendor means adding one
branch here (and the adapter class itself) — nothing else in the app changes.
"""
from __future__ import annotations

from connectors.base import SCADAAdapter, PermitAdapter, ShiftAdapter, WorkerLocationAdapter
from connectors.simulated import (
    SimulatedSCADAAdapter, SimulatedPermitAdapter, SimulatedShiftAdapter, SimulatedWorkerLocationAdapter,
)
from plant_config import PlantConfig


def build_scada_adapter(cfg: PlantConfig) -> SCADAAdapter:
    adapter = cfg.connectors.scada.adapter
    if adapter == "simulated":
        return SimulatedSCADAAdapter(cfg.zones)
    raise NotImplementedError(
        f"No SCADA adapter registered for '{adapter}'. Add one in connectors/ that "
        f"implements SCADAAdapter, then register it here."
    )


def build_permit_adapter(cfg: PlantConfig) -> PermitAdapter:
    adapter = cfg.connectors.permit_system.adapter
    if adapter == "simulated":
        return SimulatedPermitAdapter(cfg.zones)
    raise NotImplementedError(
        f"No permit-system adapter registered for '{adapter}'. Add one in connectors/ "
        f"that implements PermitAdapter, then register it here."
    )


def build_shift_adapter(cfg: PlantConfig) -> ShiftAdapter:
    adapter = cfg.connectors.shift_roster.adapter
    if adapter == "simulated":
        return SimulatedShiftAdapter(cfg.shifts, cfg.plant.timezone)
    raise NotImplementedError(
        f"No shift-roster adapter registered for '{adapter}'. Add one in connectors/ "
        f"that implements ShiftAdapter, then register it here."
    )


def build_worker_location_adapter(cfg: PlantConfig, permit_adapter: PermitAdapter) -> WorkerLocationAdapter:
    # Takes the already-built permit adapter rather than constructing its own, so
    # worker locations reflect the exact same active permits the rest of the app sees
    # — not a second, disconnected in-memory permit list.
    adapter = cfg.connectors.worker_location.adapter
    if adapter == "simulated":
        return SimulatedWorkerLocationAdapter(permit_adapter, [z.id for z in cfg.zones])
    raise NotImplementedError(
        f"No worker-location adapter registered for '{adapter}'. Add one in connectors/ "
        f"that implements WorkerLocationAdapter, then register it here."
    )
