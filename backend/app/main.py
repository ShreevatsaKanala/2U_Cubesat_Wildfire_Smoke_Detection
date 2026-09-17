from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio
import json
import os

from app.core.config import settings
from app.simulation.engine import SimulationEngine
from app.services.telemetry_service import TelemetryService
from app.api.v1 import (
    health, telemetry, simulation, observations,
    environment, spacecraft, events, ground_station,
    downlink, faults
)

engine = SimulationEngine()
telemetry_service = TelemetryService()

connected_clients: set = set()
simulation_task = None
sim_loop_running = False


async def simulation_loop():
    global sim_loop_running
    sim_loop_running = True
    while sim_loop_running:
        if engine.running:
            state = engine.update(1.0)
            packet = engine.get_latest_telemetry()
            telemetry_service.update(packet)

            payload = packet.model_dump(mode="json")
            payload["type"] = "telemetry"

            # Send recent events alongside telemetry
            recent_events = engine.event_log.get_recent(3)
            payload["recent_events"] = [e.model_dump(mode="json") for e in recent_events]

            disconnected = set()
            for client in connected_clients:
                try:
                    await client.send_json(payload)
                except Exception:
                    disconnected.add(client)
            connected_clients.difference_update(disconnected)

        await asyncio.sleep(1.0 / settings.TELEMETRY_FREQUENCY_HZ)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global simulation_task, sim_loop_running
    simulation_task = asyncio.create_task(simulation_loop())
    yield
    sim_loop_running = False
    if simulation_task:
        simulation_task.cancel()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(telemetry.router)
app.include_router(simulation.router)
app.include_router(observations.router)
app.include_router(environment.router)
app.include_router(spacecraft.router)
app.include_router(events.router)
app.include_router(ground_station.router)
app.include_router(downlink.router)
app.include_router(faults.router)

data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
if os.path.exists(data_dir):
    app.mount("/data", StaticFiles(directory=data_dir), name="data")


@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)

    latest = telemetry_service.get_latest()
    if latest:
        payload = latest.model_dump(mode="json")
        payload["type"] = "telemetry"
        try:
            await websocket.send_json(payload)
        except Exception:
            pass

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        connected_clients.discard(websocket)
    except Exception:
        connected_clients.discard(websocket)
