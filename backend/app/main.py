from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio
import json
import os
import time

from app.core.config import settings
from app.core.resource_manager import (
    resource_monitor, degradation, cleanup_scheduler,
    BoundedList, TTLCache,
)
from app.simulation.engine import SimulationEngine
from app.services.telemetry_service import TelemetryService
from app.api.v1 import (
    health, telemetry, simulation, observations,
    environment, spacecraft, events, ground_station,
    downlink, faults
)
from app.api.v1.ai_status import router as ai_status_router
from app.api.v1.tle import router as tle_router
from app.api.v1.history import router as history_router
from app.api.v1.recovery import router as recovery_router
from app.api.v1.eps import router as eps_router
from app.api.v1.thermal import router as thermal_router
from app.api.v1.firms import router as firms_router
from app.api.v1.correlation import router as correlation_router
from app.api.v1.replay import router as replay_router
from app.api.v1.export import router as export_router
from app.core.database import init_db, close_db

engine = SimulationEngine(sim_config={"ml_mode": settings.ML_MODE, "ai_mode": settings.AI_MODE})
telemetry_service = TelemetryService()

connected_clients: set = set()
simulation_task = None
sim_loop_running = False

# ── WebSocket broadcast throttling ──────────────────────────────────
_last_broadcast_time: float = 0.0
_broadcast_interval: float = settings.WEBSOCKET_BROADCAST_INTERVAL

# ── FIRMS / TLE caches ─────────────────────────────────────────────
firms_cache = TTLCache(
    max_age_minutes=settings.FIRMS_CACHE_MAX_AGE_MINUTES,
    name="FIRMS",
)
tle_cache = TTLCache(
    max_age_minutes=settings.TLE_CACHE_MAX_AGE_HOURS * 60,
    name="TLE",
)

# ── Bounded event log for recent events broadcast ───────────────────
_bounded_recent_events = BoundedList(
    max_size=settings.MAX_EVENTS_IN_MEMORY,
    name="RecentEvents",
)

# Register caches for periodic cleanup
cleanup_scheduler.register(firms_cache)
cleanup_scheduler.register(tle_cache)


async def simulation_loop():
    global sim_loop_running, _last_broadcast_time
    sim_loop_running = True
    min_tick_interval = 1.0 / settings.MAX_SIM_ITERATIONS_PER_SECOND

    while sim_loop_running:
        tick_start = time.monotonic()

        if engine.running:
            state = engine.update(1.0)
            packet = engine.get_latest_telemetry()
            telemetry_service.update(packet)

            # Register queue sizes for monitoring
            resource_monitor.register_queue("observations", lambda: len(engine.observation_service))
            resource_monitor.register_queue("downlink_queue", engine.downlink_queue.get_queue_size)
            resource_monitor.register_queue("events", lambda: len(engine.event_log.events))
            resource_monitor.register_queue("telemetry_history", lambda: len(telemetry_service.telemetry_history))

            # Check memory and apply degradation
            mem_mb = resource_monitor.sample_memory()
            degradation.update(mem_mb)

            # Throttle WebSocket broadcasts
            now = time.monotonic()
            if now - _last_broadcast_time >= _broadcast_interval:
                _last_broadcast_time = now
                payload = packet.model_dump(mode="json")
                payload["type"] = "telemetry"

                recent_events = engine.event_log.get_recent(3)
                payload["recent_events"] = [e.model_dump(mode="json") for e in recent_events]

                # Add resource stats
                payload["resource_stats"] = {
                    "memory_mb": round(mem_mb, 1),
                    "degradation": degradation.pressure,
                }

                disconnected = set()
                for client in connected_clients:
                    try:
                        await client.send_json(payload)
                    except Exception:
                        disconnected.add(client)
                connected_clients.difference_update(disconnected)

        # Throttle the sim loop itself
        elapsed = time.monotonic() - tick_start
        sleep_time = max(0.0, min_tick_interval - elapsed)
        await asyncio.sleep(sleep_time or 1.0 / settings.TELEMETRY_FREQUENCY_HZ)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global simulation_task, sim_loop_running
    await init_db()
    cleanup_scheduler.start()
    resource_monitor.set_cache_timestamp("firms")
    resource_monitor.set_cache_timestamp("tle")
    simulation_task = asyncio.create_task(simulation_loop())
    yield
    sim_loop_running = False
    if simulation_task:
        simulation_task.cancel()
        try:
            await simulation_task
        except asyncio.CancelledError:
            pass
    cleanup_scheduler.stop()
    await close_db()


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
app.include_router(ai_status_router)
app.include_router(tle_router)
app.include_router(history_router)
app.include_router(recovery_router)
app.include_router(eps_router)
app.include_router(thermal_router)
app.include_router(firms_router)
app.include_router(correlation_router)
app.include_router(replay_router)
app.include_router(export_router)

data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
if os.path.exists(data_dir):
    app.mount("/data", StaticFiles(directory=data_dir), name="data")


# ── System resources endpoint ────────────────────────────────────────
@app.get("/api/system/resources")
async def get_system_resources():
    stats = resource_monitor.get_stats()
    stats["caches"] = {
        "firms": {"size": firms_cache.size(), "evicted": firms_cache.evicted_count},
        "tle": {"size": tle_cache.size(), "evicted": tle_cache.evicted_count},
    }
    stats["degradation"] = degradation.pressure
    stats["connected_websockets"] = len(connected_clients)
    stats["simulation_running"] = engine.running
    return stats


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
