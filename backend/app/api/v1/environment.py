from fastapi import APIRouter, Query

from app.adapters.firms import FIRMSAdapter
from app.adapters.weather import WeatherAdapter

router = APIRouter()

weather_adapter = WeatherAdapter()
firms_adapter = FIRMSAdapter()


@router.get("/api/v1/environment/weather")
async def get_weather(lat: float = Query(...), lon: float = Query(...)):
    result = await weather_adapter.get_weather(lat, lon)
    return result


@router.get("/api/v1/environment/air-quality")
async def get_air_quality(lat: float = Query(...), lon: float = Query(...)):
    result = await weather_adapter.get_air_quality(lat, lon)
    return result


@router.get("/api/v1/environment/hotspots")
async def get_hotspots(
    north: float = Query(90.0),
    south: float = Query(-90.0),
    east: float = Query(180.0),
    west: float = Query(-180.0),
    days: int = Query(1),
):
    result = await firms_adapter.get_hotspots(north, south, east, west, days)
    return {"hotspots": result}
