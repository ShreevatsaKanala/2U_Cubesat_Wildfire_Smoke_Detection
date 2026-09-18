from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class ScenarioRequest(BaseModel):
    scenario: str


class SpeedRequest(BaseModel):
    speed: float


class FaultRequest(BaseModel):
    fault_type: str


def _get_engine():
    from app.demo import demo_engine
    return demo_engine


@router.get("/api/v1/demo/status")
async def demo_status():
    engine = _get_engine()
    state = engine.get_state()
    return {
        "running": state["running"],
        "scenario": state["scenario"],
        "speed": state["speed"],
        "sim_time_s": state["sim_time_s"],
        "mission_elapsed_time": state["mission_elapsed_time"],
        "mode": state["mode"],
    }


@router.post("/api/v1/demo/start")
async def demo_start():
    engine = _get_engine()
    engine.start()
    return {"status": "started"}


@router.post("/api/v1/demo/stop")
async def demo_stop():
    engine = _get_engine()
    engine.stop()
    return {"status": "stopped"}


@router.post("/api/v1/demo/reset")
async def demo_reset():
    engine = _get_engine()
    engine.reset()
    return {"status": "reset"}


@router.post("/api/v1/demo/scenario")
async def demo_set_scenario(req: ScenarioRequest):
    engine = _get_engine()
    engine.set_scenario(req.scenario)
    return {"status": "scenario_set", "scenario": req.scenario}


@router.post("/api/v1/demo/speed")
async def demo_set_speed(req: SpeedRequest):
    engine = _get_engine()
    engine.set_speed(req.speed)
    return {"status": "speed_set", "speed": req.speed}


@router.post("/api/v1/demo/fault")
async def demo_inject_fault(req: FaultRequest):
    engine = _get_engine()
    engine.inject_fault(req.fault_type)
    return {"status": "fault_injected", "fault_type": req.fault_type}


@router.post("/api/v1/demo/clear-fault")
async def demo_clear_fault(req: FaultRequest):
    engine = _get_engine()
    engine.clear_fault(req.fault_type)
    return {"status": "fault_cleared", "fault_type": req.fault_type}


@router.get("/api/v1/demo/telemetry")
async def demo_telemetry():
    engine = _get_engine()
    return engine.get_telemetry()


@router.get("/api/v1/demo/observations")
async def demo_observations():
    engine = _get_engine()
    return {"observations": engine.get_observations()}


@router.get("/api/v1/demo/events")
async def demo_events():
    engine = _get_engine()
    return {"events": engine.get_events()}


@router.get("/api/v1/demo/downlink")
async def demo_downlink():
    engine = _get_engine()
    return engine.get_downlink_status()


@router.get("/api/v1/demo/ground-stations")
async def demo_ground_stations():
    engine = _get_engine()
    return {"stations": engine.get_ground_stations()}


@router.get("/api/v1/demo/ai")
async def demo_ai():
    engine = _get_engine()
    return engine.get_ai_status()
