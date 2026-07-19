from datetime import datetime, date, time
import enum

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    String, Float, DateTime, Date, Time, JSON, Boolean, Integer, ForeignKey, Text
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from db.database import Base


class AlertSeverity(str, enum.Enum):
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    EXTREME = "extreme"


class PermitStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    REVOKED = "revoked"


# ── Config-sourced entities (id = the string id from plant.config.yaml) ──────

class Zone(Base):
    __tablename__ = "zones"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    hazard_classification: Mapped[str] = mapped_column(String(20))
    boundary: Mapped[list] = mapped_column(JSON, default=list)


class Equipment(Base):
    __tablename__ = "equipment"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey("zones.id"), index=True)
    type: Mapped[str] = mapped_column(String(100))
    install_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    maintenance_status: Mapped[str] = mapped_column(String(50), default="operational")


class Sensor(Base):
    __tablename__ = "sensors"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey("zones.id"), index=True)
    equipment_id: Mapped[str | None] = mapped_column(ForeignKey("equipment.id"), nullable=True)
    sensor_type: Mapped[str] = mapped_column(String(50))
    unit: Mapped[str] = mapped_column(String(20), default="")
    warning_threshold: Mapped[float] = mapped_column(Float)
    critical_threshold: Mapped[float] = mapped_column(Float)
    extreme_threshold: Mapped[float] = mapped_column(Float)
    calibration_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class Camera(Base):
    __tablename__ = "cameras"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey("zones.id"), index=True)
    stream_url: Mapped[str] = mapped_column(String(500))


# ── Time-series (Timescale hypertable — see db/database.py) ─────────────────

class SensorReading(Base):
    __tablename__ = "sensor_readings"
    # Composite PK (id, ts): a TimescaleDB hypertable requires the partitioning column
    # to be part of every unique constraint, including the primary key.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), primary_key=True)
    sensor_id: Mapped[str] = mapped_column(ForeignKey("sensors.id"), index=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey("zones.id"), index=True)
    value: Mapped[float] = mapped_column(Float)
    quality_flag: Mapped[str] = mapped_column(String(20), default="good")


class VisionEvent(Base):
    __tablename__ = "vision_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[str] = mapped_column(ForeignKey("cameras.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(100))
    confidence: Mapped[float] = mapped_column(Float)
    snapshot_url: Mapped[str] = mapped_column(String(500), default="")
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


# ── People & time (operational data, populated via connectors) ──────────────

class Worker(Base):
    __tablename__ = "workers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(100), default="")
    certifications: Mapped[list] = mapped_column(JSON, default=list)


class Shift(Base):
    __tablename__ = "shifts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50))
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)


class ShiftAssignment(Base):
    __tablename__ = "shift_assignments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    worker_id: Mapped[int] = mapped_column(ForeignKey("workers.id"))
    shift_id: Mapped[int] = mapped_column(ForeignKey("shifts.id"))
    zone_id: Mapped[str] = mapped_column(ForeignKey("zones.id"))
    shift_date: Mapped[date] = mapped_column(Date)


class Permit(Base):
    __tablename__ = "permits"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    permit_id: Mapped[str] = mapped_column(String(50), unique=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey("zones.id"), index=True)
    worker_id: Mapped[int | None] = mapped_column(ForeignKey("workers.id"), nullable=True)
    worker_name: Mapped[str] = mapped_column(String(200), default="")
    work_type: Mapped[str] = mapped_column(String(100))
    risk_class: Mapped[str] = mapped_column(String(20), default="medium")
    status: Mapped[str] = mapped_column(String(20), default=PermitStatus.ACTIVE.value)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Knowledge & history ──────────────────────────────────────────────────────

class Regulation(Base):
    __tablename__ = "regulations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(100))
    clause_ref: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text)
    pack: Mapped[str] = mapped_column(String(100), index=True)
    # 384 dims to match embeddings/local.py's BAAI/bge-small-en-v1.5 output.
    embedding: Mapped[list | None] = mapped_column(Vector(384), nullable=True)


class Incident(Base):
    __tablename__ = "incidents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey("zones.id"), index=True)
    incident_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20))
    contributing_factors: Mapped[list] = mapped_column(JSON, default=list)
    root_cause: Mapped[str] = mapped_column(Text, default="")
    embedding: Mapped[list | None] = mapped_column(Vector(384), nullable=True)


class NearMiss(Base):
    __tablename__ = "near_misses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey("zones.id"), index=True)
    report_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str] = mapped_column(Text)
    reported_by: Mapped[str] = mapped_column(String(200), default="")
    embedding: Mapped[list | None] = mapped_column(Vector(384), nullable=True)


# ── Risk & response ───────────────────────────────────────────────────────────

class RiskAssessment(Base):
    __tablename__ = "risk_assessments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey("zones.id"), index=True)
    compound_score: Mapped[float] = mapped_column(Float)
    severity: Mapped[str] = mapped_column(String(20))
    lead_time_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    agent_outputs: Mapped[dict] = mapped_column(JSON, default=dict)
    explanation: Mapped[str] = mapped_column(Text, default="")
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    risk_assessment_id: Mapped[int | None] = mapped_column(ForeignKey("risk_assessments.id"), nullable=True)
    zone_id: Mapped[str] = mapped_column(String(64), index=True)
    severity: Mapped[str] = mapped_column(String(20))
    channel: Mapped[str] = mapped_column(String(50), default="dashboard")
    explanation: Mapped[str] = mapped_column(Text, default="")
    contributing_factors: Mapped[list] = mapped_column(JSON, default=list)
    permit_id: Mapped[str] = mapped_column(String(50), default="")
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    acknowledged_by: Mapped[str] = mapped_column(String(200), default="")
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Action(Base):
    __tablename__ = "actions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id"), index=True)
    action_type: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    human_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    executed_by: Mapped[str] = mapped_column(String(200), default="")
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EvidenceRecord(Base):
    """A frozen, immutable snapshot of exactly what the system saw at the moment a
    critical/extreme action was proposed — sensor readings, active permits, shift
    state, and the risk assessment itself. Captured once and never modified, so it can
    stand as evidence in an incident review regardless of what the live state does
    afterward."""
    __tablename__ = "evidence_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action_id: Mapped[int] = mapped_column(ForeignKey("actions.id"), index=True)
    zone_id: Mapped[str] = mapped_column(String(64), index=True)
    sensor_snapshot: Mapped[list] = mapped_column(JSON, default=list)
    permit_snapshot: Mapped[list] = mapped_column(JSON, default=list)
    shift_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    risk_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
