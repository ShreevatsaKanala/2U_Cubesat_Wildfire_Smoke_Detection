"""Export endpoints for observations and telemetry data."""
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.services.export_service import export_service

router = APIRouter()


@router.get("/api/v1/export/observations")
async def export_observations(
    format: str = Query("json", pattern="^(json|csv)$"),
):
    if format == "csv":
        return StreamingResponse(
            export_service.stream_csv(["observations"]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=observations_export.csv"},
        )
    return StreamingResponse(
        export_service.stream_json(["observations"]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=observations_export.json"},
    )


@router.get("/api/v1/export/telemetry")
async def export_telemetry(
    format: str = Query("json", pattern="^(json|csv)$"),
):
    if format == "csv":
        return StreamingResponse(
            export_service.stream_csv(["telemetry"]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=telemetry_export.csv"},
        )
    return StreamingResponse(
        export_service.stream_json(["telemetry"]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=telemetry_export.json"},
    )
