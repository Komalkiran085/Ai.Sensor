import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from simulator.sensor_simulator import SensorSimulator, ZONES
from simulator.permit_simulator import PermitSimulator
from simulator.shift_simulator import ShiftSimulator
from agents.orchestrator import Orchestrator
from ws.manager import manager
from db.database import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

sensor_sim = SensorSimulator()
permit_sim = PermitSimulator()
shift_sim = ShiftSimulator()
orchestrator = Orchestrator(sensor_sim, permit_sim, shift_sim)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    asyncio.create_task(sensor_sim.run())
    asyncio.create_task(orchestrator.run())
    logger.info("Industrial Safety AI Platform started")
    yield
    sensor_sim.stop()
    orchestrator.stop()
    logger.info("Platform shutdown")


app = FastAPI(title="Industrial Safety AI Platform", version="1.0.0", lifespan=lifespan)

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
    return {"status": "ok", "platform": "Industrial Safety AI"}


@app.get("/api/zones")
async def get_zones():
    return {z: {**info, "zone_id": z} for z, info in ZONES.items()}


@app.get("/api/sensors")
async def get_sensors():
    return sensor_sim.get_current_readings()


@app.get("/api/sensors/{zone}")
async def get_zone_sensors(zone: str):
    reading = sensor_sim.get_zone_reading(zone.upper())
    return reading or {"error": "Zone not found"}


@app.get("/api/permits")
async def get_permits():
    return permit_sim.get_active_permits()


@app.post("/api/permits/{permit_id}/suspend")
async def suspend_permit(permit_id: str):
    ok = permit_sim.suspend_permit(permit_id)
    if ok:
        await manager.broadcast("permit_suspended", {"permit_id": permit_id})
        return {"status": "suspended", "permit_id": permit_id}
    return {"error": "Permit not found"}


@app.get("/api/risks")
async def get_risks():
    return orchestrator.get_zone_risks()


@app.get("/api/alerts")
async def get_alerts():
    return orchestrator.get_all_alerts()


@app.get("/api/shift")
async def get_shift():
    return shift_sim.get_current_shift()


@app.post("/api/report/{zone}")
async def generate_report(zone: str):
    report = await orchestrator.generate_report(zone.upper())
    return {"zone": zone, "report": report}


# ── Demo scenario triggers ──────────────────────────────────────

@app.post("/api/demo/trigger-vizag")
async def trigger_vizag():
    sensor_sim.trigger_vizag_scenario()
    return {"message": "Vizag scenario triggered — Battery 3 CO rising"}


@app.post("/api/demo/reset")
async def reset_demo():
    sensor_sim.reset_scenario()
    permit_sim.reset()
    return {"message": "Scenario reset — normal operations"}


# ── WebSocket ───────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
