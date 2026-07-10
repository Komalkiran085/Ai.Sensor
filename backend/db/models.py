from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Enum as SQLEnum, Boolean
from sqlalchemy.sql import func
from db.database import Base
import enum


class AlertSeverity(str, enum.Enum):
    LOW = "low"
    WARNING = "warning"
    CRITICAL = "critical"
    EXTREME = "extreme"


class PermitStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    REVOKED = "revoked"


class SensorReading(Base):
    __tablename__ = "sensor_readings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    sensor_id = Column(String(50), nullable=False, index=True)
    zone = Column(String(100), nullable=False, index=True)
    co_ppm = Column(Float, default=0)
    h2s_ppm = Column(Float, default=0)
    methane_ppm = Column(Float, default=0)
    temperature = Column(Float, default=0)
    humidity = Column(Float, default=0)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class Permit(Base):
    __tablename__ = "permits"
    id = Column(Integer, primary_key=True, autoincrement=True)
    permit_id = Column(String(50), unique=True, nullable=False)
    worker_name = Column(String(200), nullable=False)
    worker_id = Column(String(50))
    zone = Column(String(100), nullable=False, index=True)
    work_type = Column(String(100), nullable=False)
    risk_class = Column(String(20), default="medium")
    status = Column(SQLEnum(PermitStatus), default=PermitStatus.ACTIVE)
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    zone = Column(String(100), nullable=False, index=True)
    severity = Column(SQLEnum(AlertSeverity), nullable=False)
    compound_score = Column(Float, nullable=False)
    title = Column(String(500))
    description = Column(String(5000))
    ai_explanation = Column(String(5000))
    contributing_factors = Column(JSON)
    permit_id = Column(String(50))
    acknowledged = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Incident(Base):
    __tablename__ = "incidents"
    id = Column(Integer, primary_key=True, autoincrement=True)
    zone = Column(String(100), nullable=False)
    incident_type = Column(String(100))
    description = Column(String(5000))
    severity = Column(String(20))
    outcome = Column(String(100))
    contributing_factors = Column(JSON)
    date = Column(DateTime(timezone=True))
    report = Column(String(10000))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ShiftLog(Base):
    __tablename__ = "shift_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    shift_name = Column(String(50), nullable=False)
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    changeover_active = Column(Boolean, default=False)
    personnel_count = Column(Integer, default=0)
    notes = Column(String(2000))
