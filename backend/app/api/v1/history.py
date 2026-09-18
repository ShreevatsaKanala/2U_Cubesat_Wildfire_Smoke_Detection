"""History API endpoints — paginated queries over persisted simulation data."""
import csv
import io
import json
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from typing import Optional

from app.services.persistence_service import persistence_service
from app.services.export_service import export_service

router = APIRouter()


@router.get("/api/v1/history/observations")
async def history_observations(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    min_fire_probability: Optional[float] = None,
    ai_status: Optional[str] = None,
):
    rows = await persistence_service.get_observations(
        limit=limit,
        offset=offset,
        date_from=date_from,
        date_to=date_to,
        min_fire_probability=min_fire_probability,
        ai_status=ai_status,
    )
    total = await persistence_service.count_observations()
    return {"observations": rows, "total": total, "limit": limit, "offset": offset}


@router.get("/api/v1/history/telemetry")
async def history_telemetry(
    limit: int = Query(100, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    rows = await persistence_service.get_telemetry(
        limit=limit, offset=offset, date_from=date_from, date_to=date_to,
    )
    return {"telemetry": rows, "limit": limit, "offset": offset}


@router.get("/api/v1/history/events")
async def history_events(
    limit: int = Query(100, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    rows = await persistence_service.get_events(
        limit=limit,
        offset=offset,
        event_type=event_type,
        severity=severity,
        date_from=date_from,
        date_to=date_to,
    )
    return {"events": rows, "limit": limit, "offset": offset}


@router.get("/api/v1/history/stats")
async def history_stats():
    return await persistence_service.get_stats()


@router.get("/api/v1/history/export")
async def history_export(
    format: str = Query("json", pattern="^(json|csv)$"),
    types: str = Query("observations,telemetry,events", description="Comma-separated export types"),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    event_type: Optional[str] = None,
):
    export_types = [t.strip() for t in types.split(",") if t.strip()]

    if format == "csv":
        return StreamingResponse(
            export_service.stream_csv(export_types, date_from, date_to, event_type),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=simulation_export.csv"},
        )

    return StreamingResponse(
        export_service.stream_json(export_types, date_from, date_to, event_type),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=simulation_export.json"},
    )
