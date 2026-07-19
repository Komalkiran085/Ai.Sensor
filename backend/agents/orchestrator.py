"""Orchestrator — the tick loop that wires connectors, specialist agents, the
Coordinator, automation policy, and persistence together. Everything plant-specific
here comes from PlantConfig; nothing about a specific plant is hardcoded.
"""
from __future__ import annotations
import asyncio
import logging
import time
from datetime import datetime, timezone

from sqlalchemy import select

from agents.automation import proposes_action, requires_confirmation
from agents.compliance_agent import ComplianceAgent
from agents.coordinator import combine, compliance_query_text
from agents.gas_agent import GasAgent
from agents.incident_agent import IncidentAgent
from agents.permit_agent import PermitAgent
from agents.shift_agent import ShiftAgent
from ai.alert_generator import generate_alert_explanation, generate_incident_report, immediate_alert_text
from connectors.base import PermitAdapter, SCADAAdapter, ShiftAdapter
from db.database import async_session
from db.models import Action, Alert, EvidenceRecord, Permit, RiskAssessment, SensorReading
from embeddings.base import Embedder
from notifications.webhook import send_alert_notification
from plant_config import PlantConfig
from ws.manager import manager

logger = logging.getLogger(__name__)

ACTIVE_SEVERITIES = ("warning", "critical", "extreme")
SEVERITY_RANK = {"normal": 0, "warning": 1, "critical": 2, "extreme": 3}

# Minimum gap between alerts for the same zone when severity ISN'T getting worse — a
# noisy sensor flapping critical/warning/critical every tick would otherwise fire an
# alert every 5 seconds. An escalation (danger increasing) always fires immediately
# regardless of this window; only repeats and de-escalations get throttled.
ALERT_COOLDOWN_SECONDS = 45

# How often an unconfirmed action re-notifies — like a fire panel that keeps sounding
# until someone acknowledges it, instead of alerting once and going quiet.
PENDING_ACTION_REMINDER_SECONDS = 60


class Orchestrator:
    def __init__(
        self, cfg: PlantConfig, scada: SCADAAdapter, permits: PermitAdapter, shifts: ShiftAdapter,
        embedder: Embedder | None = None,
    ):
        self.cfg = cfg
        self.scada = scada
        self.permits = permits
        self.shifts = shifts

        self.gas_agent = GasAgent()
        self.permit_agent = PermitAgent()
        self.shift_agent = ShiftAgent()
        self.compliance_agent = ComplianceAgent(embedder) if cfg.agents.compliance_agent else None
        self.incident_agent = IncidentAgent(embedder) if cfg.agents.incident_agent else None

        self._running = False
        self._last_alert: dict[str, dict] = {}  # zone_id -> {"severity": str, "time": float}
        self._last_reminder_sent: dict[int, float] = {}  # action_id -> time.time()
        self.zone_risks: dict[str, dict] = {}

    async def run(self):
        self._running = True
        logger.info("Orchestrator started (%d zones)", len(self.cfg.zones))
        while self._running:
            try:
                await self._tick()
            except Exception:
                logger.exception("Orchestrator tick failed")
            await asyncio.sleep(5)

    def stop(self):
        self._running = False

    async def _tick(self):
        readings_by_zone = await self.scada.get_readings()
        shift = self.shifts.get_current_shift()

        async with async_session() as session:
            # The permit adapter is the source of truth (in production, a real
            # permit-to-work system); mirror its active permits into our own table so
            # compliance checks and the audit trail can query real persisted data
            # instead of state that only ever lived in the adapter's memory.
            await self._sync_permits(session, await self.permits.get_active_permits())
            await self._check_pending_reminders(session)

            for zone_cfg in self.cfg.zones:
                readings = readings_by_zone.get(zone_cfg.id, [])

                for r in readings:
                    session.add(SensorReading(sensor_id=r["sensor_id"], zone_id=zone_cfg.id, value=r["value"]))
                await session.flush()  # so the Gas Agent's trend query sees this tick's readings

                permits = await self.permits.get_permits_for_zone(zone_cfg.id)

                gas_out = await self.gas_agent.assess(session, zone_cfg, readings)
                permit_out = self.permit_agent.assess(permits)
                shift_out = self.shift_agent.assess(shift)

                query_text = compliance_query_text(gas_out, permit_out)

                compliance_out = None
                if self.compliance_agent:
                    compliance_out = await self.compliance_agent.assess(session, self.cfg.regulation_pack, query_text)

                incident_out = None
                if self.incident_agent:
                    incident_out = await self.incident_agent.assess(session, query_text)

                risk = combine(gas_out, permit_out, shift_out, compliance_out, incident_out)

                risk_row = RiskAssessment(
                    zone_id=zone_cfg.id,
                    compound_score=risk["compound_score"],
                    severity=risk["severity"],
                    lead_time_minutes=risk["lead_time_minutes"],
                    agent_outputs=risk["agent_outputs"],
                )
                session.add(risk_row)
                await session.flush()

                self.zone_risks[zone_cfg.id] = {
                    "zone_id": zone_cfg.id,
                    "zone_name": zone_cfg.name,
                    "readings": readings,
                    "risk": risk,
                    "shift": shift,
                    "permits": permits,
                }

                await manager.broadcast("sensor_update", {
                    "zone_id": zone_cfg.id, "readings": readings, "risk": risk,
                })

                if risk["severity"] in ACTIVE_SEVERITIES:
                    await self._handle_alert(session, zone_cfg, risk, readings, risk_row, permit_out, permits, shift)

            await session.commit()

        await manager.broadcast("zone_risks", self.zone_risks)

    async def _handle_alert(self, session, zone_cfg, risk, readings, risk_row, permit_out, permits, shift):
        severity = risk["severity"]
        now = time.time()
        last = self._last_alert.get(zone_cfg.id)

        if last is not None:
            if severity == last["severity"]:
                return  # nothing's actually changed — never re-fire for that alone
            escalating = SEVERITY_RANK[severity] > SEVERITY_RANK[last["severity"]]
            if not escalating and (now - last["time"]) < ALERT_COOLDOWN_SECONDS:
                # A repeat or de-escalation too soon after the last alert — a noisy
                # sensor flapping critical/warning/critical would otherwise fire every
                # tick. An escalation (danger increasing) always bypasses this, though.
                return

        self._last_alert[zone_cfg.id] = {"severity": severity, "time": now}

        # The alert itself must never wait on AI generation — Claude is a couple of
        # seconds, but a local model on CPU can take tens of seconds, and a safety
        # alert delayed that long defeats the point. Fire instantly with fast,
        # deterministic text; upgrade it in place once the real explanation is ready.
        explanation = immediate_alert_text(zone_cfg.name, risk, readings)
        risk_row.explanation = explanation

        active_permit = permit_out.get("active_permit")
        alert_row = Alert(
            risk_assessment_id=risk_row.id,
            zone_id=zone_cfg.id,
            severity=risk["severity"],
            explanation=explanation,
            contributing_factors=risk["contributing_factors"],
            permit_id=active_permit["permit_id"] if active_permit else "",
        )
        session.add(alert_row)
        await session.flush()

        await manager.broadcast("alert", {
            "id": alert_row.id,
            "zone_id": zone_cfg.id,
            "zone_name": zone_cfg.name,
            "severity": risk["severity"],
            "compound_score": risk["compound_score"],
            "lead_time_minutes": risk["lead_time_minutes"],
            "explanation": explanation,
            "contributing_factors": risk["contributing_factors"],
            "permit": active_permit,
            "sent_at": (alert_row.sent_at or datetime.now(timezone.utc)).isoformat(),
        })

        # Critical/extreme reaches beyond the dashboard — a real channel, not just a
        # browser beep, so this doesn't depend on someone having the tab open. Uses the
        # instant text too, for the same reason: notification speed matters more than polish.
        if risk["severity"] in ("critical", "extreme"):
            await send_alert_notification(zone_cfg.name, risk["severity"], explanation, risk["compound_score"])

        asyncio.create_task(self._enrich_alert(alert_row.id, zone_cfg.name, risk, readings))

        if not proposes_action(risk["severity"]):
            return

        hazard_type = active_permit["work_type"] if active_permit else None
        needs_confirm = requires_confirmation(risk["severity"], hazard_type, self.cfg.automation)

        if risk["severity"] == "extreme":
            action_type = "evacuate_zone"
        elif active_permit:
            action_type = "suspend_permit"
        else:
            action_type = "notify_supervisor"

        action_row = Action(
            alert_id=alert_row.id,
            action_type=action_type,
            status="pending_confirmation" if needs_confirm else "auto_executed",
            human_confirmed=not needs_confirm,
        )
        session.add(action_row)
        await session.flush()

        # Freeze the evidence now, at proposal time — not if/when a human confirms —
        # so the record reflects exactly what the system saw, independent of how long
        # confirmation takes.
        evidence = EvidenceRecord(
            action_id=action_row.id,
            zone_id=zone_cfg.id,
            sensor_snapshot=readings,
            permit_snapshot=permits,
            shift_snapshot=shift,
            risk_snapshot={
                "compound_score": risk["compound_score"],
                "severity": risk["severity"],
                "lead_time_minutes": risk["lead_time_minutes"],
                "contributing_factors": risk["contributing_factors"],
            },
        )
        session.add(evidence)
        await session.flush()

        await manager.broadcast("action_proposed", {
            "id": action_row.id,
            "alert_id": alert_row.id,
            "zone_id": zone_cfg.id,
            "action_type": action_row.action_type,
            "status": action_row.status,
            "evidence_id": evidence.id,
        })

    async def _enrich_alert(self, alert_id: int, zone_name: str, risk: dict, readings: list[dict]) -> None:
        """Runs in the background, off the tick's critical path. Generates the real
        AI explanation (Claude or the local model, per LLM_PROVIDER) and updates the
        alert in place once ready — the alert itself already fired with instant text."""
        try:
            explanation = await generate_alert_explanation(zone_name, risk, readings)
        except Exception:
            logger.exception("Alert enrichment failed for alert %s", alert_id)
            return

        async with async_session() as session:
            alert = await session.get(Alert, alert_id)
            if alert is None:
                return
            alert.explanation = explanation
            await session.commit()

        await manager.broadcast("alert_updated", {"id": alert_id, "explanation": explanation})

    async def _sync_permits(self, session, permits: list[dict]) -> None:
        for p in permits:
            result = await session.execute(select(Permit).where(Permit.permit_id == p["permit_id"]))
            row = result.scalar_one_or_none()
            if row is None:
                row = Permit(permit_id=p["permit_id"])
                session.add(row)
            row.zone_id = p["zone_id"]
            row.worker_name = p.get("worker_name", "")
            row.work_type = p["work_type"]
            row.risk_class = p.get("risk_class", "medium")
            row.status = p.get("status", "active")
            row.start_time = _parse_dt(p.get("start_time"))
            row.end_time = _parse_dt(p.get("end_time"))
        await session.flush()

    async def _check_pending_reminders(self, session) -> None:
        """Re-notifies for every action still awaiting confirmation, on a fixed
        interval — a fire panel keeps sounding until acknowledged, it doesn't chime
        once and go quiet. Runs every tick; only actually sends once the interval
        has genuinely elapsed since the last reminder (or since creation, for the
        first one)."""
        now = time.time()
        result = await session.execute(
            select(Action, Alert, RiskAssessment.compound_score)
            .join(Alert, Action.alert_id == Alert.id)
            .join(RiskAssessment, Alert.risk_assessment_id == RiskAssessment.id, isouter=True)
            .where(Action.status == "pending_confirmation")
        )
        for action, alert, compound_score in result.all():
            last_sent = self._last_reminder_sent.get(action.id, action.created_at.timestamp())
            if now - last_sent < PENDING_ACTION_REMINDER_SECONDS:
                continue
            self._last_reminder_sent[action.id] = now

            pending_minutes = round((now - action.created_at.timestamp()) / 60, 1)
            zone_cfg = self.cfg.zone(alert.zone_id)
            zone_name = zone_cfg.name if zone_cfg else alert.zone_id

            await manager.broadcast("action_reminder", {
                "id": action.id,
                "alert_id": action.alert_id,
                "zone_id": alert.zone_id,
                "zone_name": zone_name,
                "action_type": action.action_type,
                "severity": alert.severity,
                "pending_minutes": pending_minutes,
            })
            await send_alert_notification(
                zone_name, alert.severity,
                f"Reminder — still awaiting confirmation to {action.action_type.replace('_', ' ')} "
                f"({pending_minutes} min and counting).",
                compound_score or 0.0,
            )

    async def generate_report(self, zone_id: str) -> str:
        data = self.zone_risks.get(zone_id)
        if not data:
            return "No data available for this zone yet."
        return await generate_incident_report(data["zone_name"], data["risk"], data["readings"])

    def get_zone_risks(self) -> dict:
        return dict(self.zone_risks)

    def reset_debounce(self) -> None:
        """Forget every zone's last-seen severity and any pending-action reminder
        timers, so a demo reset starts genuinely clean instead of the next tick
        silently comparing against stale state."""
        self._last_alert = {}
        self._last_reminder_sent = {}


def _parse_dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None
