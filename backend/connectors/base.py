"""Connector adapter interfaces. One interface per data source, many possible
implementations behind it (see docs/SYSTEM_DESIGN.md §3, mechanism 1: "connector adapters").

Onboarding a new plant with a different SCADA vendor means writing one new class that
implements SCADAAdapter — nothing upstream of this interface changes.
"""
from __future__ import annotations
from abc import ABC, abstractmethod


class SCADAAdapter(ABC):
    """Gives current sensor readings for every zone. A real implementation speaks
    OPC-UA/Modbus/vendor-specific protocol to the plant's SCADA system; the rest of the
    app only ever calls get_readings()."""

    @abstractmethod
    async def get_readings(self) -> dict[str, list[dict]]:
        """zone_id -> [{"sensor_id": "S-47", "sensor_type": "co_ppm", "value": 38.2}, ...]"""
        ...


class PermitAdapter(ABC):
    """Reads and mutates work permits. A real implementation calls out to whatever
    permit-to-work software the plant runs."""

    @abstractmethod
    async def get_permits_for_zone(self, zone_id: str) -> list[dict]: ...

    @abstractmethod
    async def get_active_permits(self) -> list[dict]: ...

    @abstractmethod
    async def suspend_permit(self, permit_id: str) -> bool: ...


class ShiftAdapter(ABC):
    """Reports the current shift and changeover/fatigue state. A real implementation
    reads the plant's HR/roster system."""

    @abstractmethod
    def get_current_shift(self) -> dict: ...


class WorkerLocationAdapter(ABC):
    """Reports which zone each worker is currently in. Deliberately zone-level, not a
    precise (x, y) position — that's what a real badge/RFID zone-entry system actually
    gives you; true indoor positioning (UWB/RTLS) is a much bigger and more expensive
    integration that most plants don't have. A real implementation reads the plant's
    access-control/badge system."""

    @abstractmethod
    async def get_worker_locations(self) -> list[dict]:
        """[{"worker_id": str, "name": str, "zone_id": str, "role": str}, ...]"""
        ...
