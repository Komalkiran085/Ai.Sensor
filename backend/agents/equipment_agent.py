"""Equipment Agent — checks whether the equipment installed in a zone is in a state
that makes hazardous work there riskier, independent of what the sensors or permits
say. The Coordinator is what notices when degraded equipment combines with an active
permit or elevated gas into something worse than any one of them alone — the same
"compound" reasoning as the Gas/Permit/Shift agents, just for a fourth real signal."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Equipment

# Scaled to the same magnitude as the Shift Agent's fatigue/changeover factor (max 0.4)
# rather than the same 0-1 scale as Gas/Permit — this is a background condition that
# makes an active hazard worse, not a standalone trigger. Degraded equipment plus an
# active hazardous permit should be able to tip warning into critical; it shouldn't,
# alone, be able to manufacture an automatic evacuation call out of normal gas readings.
STATUS_RISK = {
    "operational": 0.0,
    "under_maintenance": 0.15,
    "faulty": 0.25,
    "offline": 0.35,
}


class EquipmentAgent:
    async def assess(self, session: AsyncSession, zone_id: str) -> dict:
        result = await session.execute(select(Equipment).where(Equipment.zone_id == zone_id))
        equipment = result.scalars().all()

        factor = 0.0
        details = []
        for eq in equipment:
            status = eq.maintenance_status
            risk = STATUS_RISK.get(status, 0.15)  # an unrecognized status is treated as degraded, not operational
            if risk > 0:
                details.append(f"{eq.id} ({eq.type.replace('_', ' ')}): {status.replace('_', ' ')}")
            factor = max(factor, risk)

        return {"agent": "equipment", "score": factor, "details": details}
