from fastapi import APIRouter, HTTPException, Query
from app.services.ground_network import ground_network_service

router = APIRouter()


@router.get("/api/v1/ground-station/status")
async def get_ground_station_status():
    from app.main import engine
    return engine.get_ground_pass()


@router.get("/api/v1/ground-station/config")
async def get_ground_station_config():
    from app.main import engine
    return engine.ground_station.model_dump(mode="json")


@router.get("/api/v1/ground-station/network")
async def get_ground_station_network():
    stations = ground_network_service.get_all_stations()
    active_id = ground_network_service.get_active_station_id()
    return {
        "stations": [s.model_dump() for s in stations],
        "active_station_id": active_id,
        "network_id": ground_network_service.network.network_id,
    }


@router.get("/api/v1/ground-stations")
async def list_ground_stations():
    stations = ground_network_service.get_all_stations()
    active_id = ground_network_service.get_active_station_id()
    return {
        "stations": [s.model_dump() for s in stations],
        "active_station_id": active_id,
        "network_id": ground_network_service.network.network_id,
    }


@router.get("/api/v1/ground-stations/{station_id}")
async def get_station_detail(station_id: str):
    station = ground_network_service.get_station(station_id)
    if not station:
        raise HTTPException(status_code=404, detail=f"Station {station_id} not found")
    return station.model_dump()


@router.get("/api/v1/ground-stations/visibility")
async def compute_visibility(
    lat: float = Query(..., description="Satellite latitude in degrees"),
    lon: float = Query(..., description="Satellite longitude in degrees"),
    alt: float = Query(408.0, description="Satellite altitude in km"),
):
    visibilities = ground_network_service.compute_visibility(lat, lon, alt)
    best = ground_network_service.select_best_station(lat, lon, alt)
    handoff = ground_network_service.handle_handoff(lat, lon, alt)
    return {
        "satellite": {"latitude": lat, "longitude": lon, "altitude_km": alt},
        "stations": [v.model_dump() for v in visibilities],
        "best_station": best.model_dump() if best else None,
        "active_station_id": ground_network_service.get_active_station_id(),
        "handoff": handoff.model_dump() if handoff else None,
    }


@router.post("/api/v1/ground-stations/{station_id}/toggle")
async def toggle_station(station_id: str):
    station = ground_network_service.toggle_station(station_id)
    if not station:
        raise HTTPException(status_code=404, detail=f"Station {station_id} not found")
    return {
        "station_id": station.station_id,
        "name": station.name,
        "status": station.status.value,
    }


@router.get("/api/v1/ground-stations/network/quality")
async def estimate_pass_quality(
    lat: float = Query(..., description="Satellite latitude in degrees"),
    lon: float = Query(..., description="Satellite longitude in degrees"),
    alt: float = Query(408.0, description="Satellite altitude in km"),
):
    return ground_network_service.estimate_pass_quality(lat, lon, alt)


@router.get("/api/v1/ground-stations/network/handoffs")
async def get_handoff_history():
    history = ground_network_service.get_handoff_history()
    return {
        "handoffs": [h.model_dump() for h in history],
        "active_station_id": ground_network_service.get_active_station_id(),
    }
