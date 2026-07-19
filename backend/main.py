import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, desc, and_, update

from agents.compliance_checks import run_compliance_checks
from agents.orchestrator import Orchestrator
from bootstrap import bootstrap
from connectors.registry import (
    build_permit_adapter, build_scada_adapter, build_shift_adapter, build_worker_location_adapter,
)
from db.database import async_session, init_db
from db.models import Action, Alert, EvidenceRecord, Incident, NearMiss, Permit, Regulation, RiskAssessment
from embeddings.local import LocalEmbedder
from knowledge.seed_incidents import INCIDENTS, NEAR_MISSES
from knowledge.seed_regulations import REGULATIONS
from plant_config import PlantConfig
from ws.manager import manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

plant_cfg: PlantConfig | None = None
orchestrator: Orchestrator | None = None
scada_adapter = None
permit_adapter = None
shift_adapter = None
worker_location_adapter = None
embedder = LocalEmbedder()


async def seed_knowledge(pack: str) -> None:
    async with async_session() as session:
        existing = await session.execute(select(Regulation).where(Regulation.pack == pack).limit(1))
        if existing.first():
            return
        regs = REGULATIONS.get(pack, [])
        for reg in regs:
            vector = await asyncio.to_thread(embedder.embed_passage, reg["content"])
            session.add(Regulation(
                source=reg["source"], clause_ref=reg["clause_ref"], content=reg["content"],
                pack=pack, embedding=vector,
            ))
        await session.commit()
        logger.info("Seeded %d regulation clauses (with embeddings) for pack '%s'", len(regs), pack)


async def seed_incident_history() -> None:
    async with async_session() as session:
        existing = await session.execute(select(Incident).limit(1))
        if existing.first():
            return
        for inc in INCIDENTS:
            vector = await asyncio.to_thread(embedder.embed_passage, inc["description"])
            session.add(Incident(
                zone_id=inc["zone_id"], incident_date=date.fromisoformat(inc["incident_date"]),
                description=inc["description"], severity=inc["severity"],
                contributing_factors=inc["contributing_factors"], root_cause=inc["root_cause"],
                embedding=vector,
            ))
        for nm in NEAR_MISSES:
            vector = await asyncio.to_thread(embedder.embed_passage, nm["description"])
            session.add(NearMiss(
                zone_id=nm["zone_id"], report_date=date.fromisoformat(nm["report_date"]),
                description=nm["description"], reported_by=nm["reported_by"], embedding=vector,
            ))
        await session.commit()
        logger.info("Seeded %d incidents + %d near-misses (with embeddings)", len(INCIDENTS), len(NEAR_MISSES))


@asynccontextmanager
async def lifespan(app: FastAPI):
    global plant_cfg, orchestrator, scada_adapter, permit_adapter, shift_adapter, worker_location_adapter

    await init_db()
    plant_cfg = await bootstrap()
    await seed_knowledge(plant_cfg.regulation_pack)
    await seed_incident_history()

    scada_adapter = build_scada_adapter(plant_cfg)
    permit_adapter = build_permit_adapter(plant_cfg)
    shift_adapter = build_shift_adapter(plant_cfg)
    worker_location_adapter = build_worker_location_adapter(plant_cfg, permit_adapter)

    orchestrator = Orchestrator(plant_cfg, scada_adapter, permit_adapter, shift_adapter, embedder)
    asyncio.create_task(orchestrator.run())
    logger.info("Industrial Safety AI Platform started — plant: %s (%d zones)", plant_cfg.plant.name, len(plant_cfg.zones))
    yield
    orchestrator.stop()
    logger.info("Platform shutdown")


app = FastAPI(title="Industrial Safety AI Platform", version="2.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── REST endpoints ──────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "platform": "Industrial Safety AI", "plant": plant_cfg.plant.name if plant_cfg else None}


@app.get("/api/plant")
async def get_plant():
    return plant_cfg.plant.model_dump()


@app.get("/api/zones")
async def get_zones():
    return {
        z.id: {
            "zone_id": z.id,
            "name": z.name,
            "hazard_classification": z.hazard_classification,
            "boundary": z.boundary,
        }
        for z in plant_cfg.zones
    }


@app.get("/api/sensors")
async def get_sensors():
    return await scada_adapter.get_readings()


@app.get("/api/permits")
async def get_permits():
    return await permit_adapter.get_active_permits()


@app.get("/api/workers")
async def get_workers():
    return await worker_location_adapter.get_worker_locations()


@app.post("/api/permits/{permit_id}/suspend")
async def suspend_permit(permit_id: str):
    ok = await permit_adapter.suspend_permit(permit_id)
    if ok:
        await _mark_permit_suspended_in_db(permit_id)
        await manager.broadcast("permit_status_changed", {"permit_id": permit_id, "status": "suspended"})
        return {"status": "suspended", "permit_id": permit_id}
    return {"error": "Permit not found"}


async def _mark_permit_suspended_in_db(permit_id: str) -> None:
    async with async_session() as session:
        result = await session.execute(select(Permit).where(Permit.permit_id == permit_id))
        row = result.scalar_one_or_none()
        if row:
            row.status = "suspended"
            await session.commit()


@app.get("/api/compliance")
async def get_compliance():
    """Real compliance status, computed from actual sensor/permit/equipment data —
    not the static illustrative list this panel used to show."""
    async with async_session() as session:
        checks = await run_compliance_checks(session, plant_cfg, orchestrator.get_zone_risks())
    return {
        "checks": checks,
        "passed": sum(1 for c in checks if c["status"] == "pass"),
        "failed": sum(1 for c in checks if c["status"] == "fail"),
        "unmonitored": sum(1 for c in checks if c["status"] == "unmonitored"),
    }


@app.get("/api/risks")
async def get_risks():
    return orchestrator.get_zone_risks()


@app.get("/api/alerts")
async def get_alerts(limit: int = 50):
    async with async_session() as session:
        result = await session.execute(
            select(Alert, RiskAssessment.compound_score, RiskAssessment.lead_time_minutes)
            .join(RiskAssessment, Alert.risk_assessment_id == RiskAssessment.id, isouter=True)
            .order_by(desc(Alert.sent_at))
            .limit(limit)
        )
        zone_names = {z.id: z.name for z in plant_cfg.zones}
        return [
            {
                "id": a.id,
                "zone_id": a.zone_id,
                "zone_name": zone_names.get(a.zone_id, a.zone_id),
                "severity": a.severity,
                "compound_score": compound_score,
                "lead_time_minutes": lead_time_minutes,
                "explanation": a.explanation,
                "contributing_factors": a.contributing_factors,
                "permit_id": a.permit_id,
                "sent_at": a.sent_at.isoformat() if a.sent_at else None,
                "acknowledged_by": a.acknowledged_by,
            }
            for a, compound_score, lead_time_minutes in result.all()
        ]


@app.get("/api/audit")
async def get_audit_trail(
    zone_id: str | None = None,
    severity: str | None = None,
    limit: int = 200,
    offset: int = 0,
):
    """The full audit trail: every alert ever fired, joined with the risk score that
    triggered it and whatever action was proposed/confirmed in response — including
    who confirmed it and when. This is the data behind "prove what happened" for a
    regulator or an internal review; it was always being recorded, just never surfaced."""
    async with async_session() as session:
        query = (
            select(Alert, RiskAssessment.compound_score, RiskAssessment.lead_time_minutes, Action, EvidenceRecord.id)
            .join(RiskAssessment, Alert.risk_assessment_id == RiskAssessment.id, isouter=True)
            .join(Action, Action.alert_id == Alert.id, isouter=True)
            .join(EvidenceRecord, EvidenceRecord.action_id == Action.id, isouter=True)
        )
        conditions = []
        if zone_id:
            conditions.append(Alert.zone_id == zone_id)
        if severity:
            conditions.append(Alert.severity == severity)
        if conditions:
            query = query.where(and_(*conditions))
        query = query.order_by(desc(Alert.sent_at)).limit(limit).offset(offset)

        result = await session.execute(query)
        zone_names = {z.id: z.name for z in plant_cfg.zones}
        rows = []
        for alert, compound_score, lead_time_minutes, action, evidence_id in result.all():
            rows.append({
                "alert_id": alert.id,
                "zone_id": alert.zone_id,
                "zone_name": zone_names.get(alert.zone_id, alert.zone_id),
                "severity": alert.severity,
                "compound_score": compound_score,
                "lead_time_minutes": lead_time_minutes,
                "explanation": alert.explanation,
                "contributing_factors": alert.contributing_factors,
                "permit_id": alert.permit_id,
                "sent_at": alert.sent_at.isoformat() if alert.sent_at else None,
                "action": ({
                    "id": action.id,
                    "action_type": action.action_type,
                    "status": action.status,
                    "human_confirmed": action.human_confirmed,
                    "executed_by": action.executed_by,
                    "executed_at": action.executed_at.isoformat() if action.executed_at else None,
                    "evidence_id": evidence_id,
                } if action else None),
            })
        return rows


@app.get("/api/evidence/{evidence_id}")
async def get_evidence(evidence_id: int):
    """The frozen snapshot behind a proposed action — sensor readings, permits, shift
    state, and risk assessment exactly as they stood at the moment the action was
    proposed, regardless of what happened afterward."""
    async with async_session() as session:
        evidence = await session.get(EvidenceRecord, evidence_id)
        if not evidence:
            return {"error": "Evidence record not found"}
        return {
            "id": evidence.id,
            "action_id": evidence.action_id,
            "zone_id": evidence.zone_id,
            "captured_at": evidence.captured_at.isoformat() if evidence.captured_at else None,
            "sensor_snapshot": evidence.sensor_snapshot,
            "permit_snapshot": evidence.permit_snapshot,
            "shift_snapshot": evidence.shift_snapshot,
            "risk_snapshot": evidence.risk_snapshot,
        }


@app.get("/api/actions/pending")
async def get_pending_actions():
    async with async_session() as session:
        result = await session.execute(
            select(Action, Alert.zone_id, EvidenceRecord.id)
            .join(Alert, Action.alert_id == Alert.id)
            .join(EvidenceRecord, EvidenceRecord.action_id == Action.id, isouter=True)
            .where(Action.status == "pending_confirmation")
        )
        return [
            {
                "id": a.id, "alert_id": a.alert_id, "zone_id": zone_id,
                "action_type": a.action_type, "status": a.status, "evidence_id": evidence_id,
            }
            for a, zone_id, evidence_id in result.all()
        ]


@app.post("/api/actions/{action_id}/confirm")
async def confirm_action(action_id: int, confirmed_by: str = "safety_officer"):
    """The human-in-loop gateway: state-changing actions (suspend a permit, etc.)
    that the automation policy flagged as needing confirmation wait here for exactly
    one click before anything actually happens."""
    async with async_session() as session:
        action = await session.get(Action, action_id)
        if not action:
            return {"error": "Action not found"}
        alert = await session.get(Alert, action.alert_id)

        if action.action_type == "suspend_permit" and alert and alert.permit_id:
            await permit_adapter.suspend_permit(alert.permit_id)
            permit_result = await session.execute(select(Permit).where(Permit.permit_id == alert.permit_id))
            permit_row = permit_result.scalar_one_or_none()
            if permit_row:
                permit_row.status = "suspended"
            await manager.broadcast("permit_status_changed", {"permit_id": alert.permit_id, "status": "suspended"})

        if action.action_type == "evacuate_zone" and alert:
            # Worker presence is derived live from active permits in the zone (see
            # SimulatedWorkerLocationAdapter) — an evacuation that doesn't suspend
            # those permits leaves the worker showing as still "present" forever.
            zone_permits = await permit_adapter.get_permits_for_zone(alert.zone_id)
            for p in zone_permits:
                await permit_adapter.suspend_permit(p["permit_id"])
                permit_result = await session.execute(select(Permit).where(Permit.permit_id == p["permit_id"]))
                permit_row = permit_result.scalar_one_or_none()
                if permit_row:
                    permit_row.status = "suspended"
                await manager.broadcast("permit_status_changed", {"permit_id": p["permit_id"], "status": "suspended"})

        action.status = "executed"
        action.human_confirmed = True
        action.executed_by = confirmed_by
        action.executed_at = datetime.now(timezone.utc)
        await session.commit()

    await manager.broadcast("action_confirmed", {"id": action_id, "action_type": action.action_type})
    return {"status": "executed", "action_id": action_id}


@app.get("/api/shift")
async def get_shift():
    return shift_adapter.get_current_shift()


@app.post("/api/report/{zone_id}")
async def generate_report(zone_id: str):
    report = await orchestrator.generate_report(zone_id)
    return {"zone_id": zone_id, "report": report}


# ── Demo scenario triggers (only meaningful with the simulated SCADA adapter) ────

@app.get("/api/demo/scenarios")
async def get_demo_scenarios():
    return [s.model_dump() for s in plant_cfg.demo_scenarios]



@app.post("/api/demo/trigger-scenario/{zone_id}")
async def trigger_scenario(zone_id: str):
    if hasattr(scada_adapter, "trigger_scenario"):
        scada_adapter.trigger_scenario(zone_id)
        return {"message": f"Scenario triggered for {zone_id}"}
    return {"error": "Current SCADA adapter does not support demo scenarios"}


@app.post("/api/demo/reset")
async def reset_demo():
    """A genuinely full reset — not just the gas ramp. Also reactivates any permits
    suspended during the demo, cancels (not "executes") any actions still awaiting
    confirmation, and clears the orchestrator's per-zone debounce memory, so repeated
    demo runs don't accumulate stale suspended permits and orphaned pending actions."""
    if not hasattr(scada_adapter, "reset_scenario"):
        return {"error": "Current SCADA adapter does not support demo scenarios"}

    scada_adapter.reset_scenario()
    orchestrator.reset_debounce()

    reactivated_ids = permit_adapter.reset() if hasattr(permit_adapter, "reset") else []

    async with async_session() as session:
        if reactivated_ids:
            await session.execute(
                update(Permit).where(Permit.permit_id.in_(reactivated_ids)).values(status="active")
            )
        result = await session.execute(
            update(Action).where(Action.status == "pending_confirmation").values(status="cancelled")
            .returning(Action.id)
        )
        cancelled_ids = [row[0] for row in result.all()]
        await session.commit()

    for permit_id in reactivated_ids:
        await manager.broadcast("permit_status_changed", {"permit_id": permit_id, "status": "active"})
    for action_id in cancelled_ids:
        await manager.broadcast("action_confirmed", {"id": action_id, "action_type": "cancelled"})

    return {
        "message": "Scenario reset — normal operations",
        "permits_reactivated": len(reactivated_ids),
        "actions_cancelled": len(cancelled_ids),
    }


# ── WebSocket ───────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
