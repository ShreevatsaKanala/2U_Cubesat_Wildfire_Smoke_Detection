from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.post("/api/v1/simulation/start")
async def start_simulation():
    from app.main import engine
    engine.start()
    return {"status": "started", "running": engine.running}


@router.post("/api/v1/simulation/stop")
async def stop_simulation():
    from app.main import engine
    engine.stop()
    return {"status": "stopped", "running": engine.running}


@router.post("/api/v1/simulation/reset")
async def reset_simulation():
    from app.main import engine
    engine.reset()
    return {"status": "reset", "running": engine.running}


@router.get("/api/v1/config")
async def get_config():
    from app.main import engine
    return {
        "spacecraft": {
            "spacecraft_id": engine.spacecraft_config.spacecraft_id,
            "name": engine.spacecraft_config.name,
            "mass_kg": engine.spacecraft_config.mass_kg,
            "battery_capacity_wh": engine.spacecraft_config.battery_capacity_wh,
            "solar_generation_w": engine.spacecraft_config.solar_generation_w,
            "power_consumption_w": engine.spacecraft_config.power_consumption_w,
        },
        "simulation": {
            "speed": engine.sim_speed,
            "telemetry_frequency_hz": engine.telemetry_frequency,
            "observation_interval_s": engine.observation_interval,
            "running": engine.running,
        },
    }
