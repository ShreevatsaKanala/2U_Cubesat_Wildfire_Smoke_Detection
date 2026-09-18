"""Export service — streaming export of historical data in JSON/CSV."""
import csv
import io
import json
import logging
from typing import Optional, AsyncIterator

from app.core.database import get_db
from app.services.persistence_service import persistence_service

logger = logging.getLogger(__name__)


class ExportService:
    """Provides filtered, streaming export of simulation data."""

    async def export_observations_stream(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        batch_size: int = 500,
    ) -> AsyncIterator[dict]:
        db = await get_db()
        where, params = [], []
        if date_from:
            where.append("timestamp >= ?")
            params.append(date_from)
        if date_to:
            where.append("timestamp <= ?")
            params.append(date_to)
        clause = (" WHERE " + " AND ".join(where)) if where else ""
        sql = f"SELECT * FROM observations{clause} ORDER BY timestamp"
        cursor = await db.execute(sql, params)
        while True:
            rows = await cursor.fetchmany(batch_size)
            if not rows:
                break
            for row in rows:
                yield dict(row)

    async def export_telemetry_stream(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        batch_size: int = 500,
    ) -> AsyncIterator[dict]:
        db = await get_db()
        where, params = [], []
        if date_from:
            where.append("timestamp >= ?")
            params.append(date_from)
        if date_to:
            where.append("timestamp <= ?")
            params.append(date_to)
        clause = (" WHERE " + " AND ".join(where)) if where else ""
        sql = f"SELECT * FROM telemetry_snapshots{clause} ORDER BY timestamp"
        cursor = await db.execute(sql, params)
        while True:
            rows = await cursor.fetchmany(batch_size)
            if not rows:
                break
            for row in rows:
                yield dict(row)

    async def export_events_stream(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        event_type: Optional[str] = None,
        batch_size: int = 500,
    ) -> AsyncIterator[dict]:
        db = await get_db()
        where, params = [], []
        if event_type:
            where.append("event_type = ?")
            params.append(event_type)
        if date_from:
            where.append("timestamp >= ?")
            params.append(date_from)
        if date_to:
            where.append("timestamp <= ?")
            params.append(date_to)
        clause = (" WHERE " + " AND ".join(where)) if where else ""
        sql = f"SELECT * FROM events{clause} ORDER BY timestamp"
        cursor = await db.execute(sql, params)
        while True:
            rows = await cursor.fetchmany(batch_size)
            if not rows:
                break
            for row in rows:
                yield dict(row)

    async def export_ai_analysis_stream(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        batch_size: int = 500,
    ) -> AsyncIterator[dict]:
        db = await get_db()
        where, params = [], []
        if date_from:
            where.append("timestamp >= ?")
            params.append(date_from)
        if date_to:
            where.append("timestamp <= ?")
            params.append(date_to)
        clause = (" WHERE " + " AND ".join(where)) if where else ""
        sql = f"SELECT * FROM ai_analysis{clause} ORDER BY timestamp"
        cursor = await db.execute(sql, params)
        while True:
            rows = await cursor.fetchmany(batch_size)
            if not rows:
                break
            for row in rows:
                yield dict(row)

    async def export_downlink_stream(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        batch_size: int = 500,
    ) -> AsyncIterator[dict]:
        db = await get_db()
        where, params = [], []
        if date_from:
            where.append("start_time >= ?")
            params.append(date_from)
        if date_to:
            where.append("start_time <= ?")
            params.append(date_to)
        clause = (" WHERE " + " AND ".join(where)) if where else ""
        sql = f"SELECT * FROM downlink_history{clause} ORDER BY start_time"
        cursor = await db.execute(sql, params)
        while True:
            rows = await cursor.fetchmany(batch_size)
            if not rows:
                break
            for row in rows:
                yield dict(row)

    async def export_sessions_stream(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        batch_size: int = 500,
    ) -> AsyncIterator[dict]:
        db = await get_db()
        where, params = [], []
        if date_from:
            where.append("start_time >= ?")
            params.append(date_from)
        if date_to:
            where.append("start_time <= ?")
            params.append(date_to)
        clause = (" WHERE " + " AND ".join(where)) if where else ""
        sql = f"SELECT * FROM mission_sessions{clause} ORDER BY start_time"
        cursor = await db.execute(sql, params)
        while True:
            rows = await cursor.fetchmany(batch_size)
            if not rows:
                break
            for row in rows:
                yield dict(row)

    async def stream_json(
        self,
        types: list[str],
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> AsyncIterator[str]:
        yield "{\n"
        first_type = True

        exporters = {
            "observations": lambda: self.export_observations_stream(date_from, date_to),
            "telemetry": lambda: self.export_telemetry_stream(date_from, date_to),
            "events": lambda: self.export_events_stream(date_from, date_to, event_type),
            "ai_results": lambda: self.export_ai_analysis_stream(date_from, date_to),
            "downlink": lambda: self.export_downlink_stream(date_from, date_to),
            "sessions": lambda: self.export_sessions_stream(date_from, date_to),
        }

        for export_type in types:
            if export_type not in exporters:
                continue

            if not first_type:
                yield ",\n"
            first_type = False

            yield f'  "{export_type}": [\n'
            first_item = True
            async for record in exporters[export_type]():
                if not first_item:
                    yield ",\n"
                first_item = False
                yield f"    {json.dumps(record, default=str)}"
            yield "\n  ]"

        yield "\n}"

    async def stream_csv(
        self,
        types: list[str],
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> AsyncIterator[str]:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["type", "data"])
        yield buf.getvalue()

        exporters = {
            "observations": lambda: self.export_observations_stream(date_from, date_to),
            "telemetry": lambda: self.export_telemetry_stream(date_from, date_to),
            "events": lambda: self.export_events_stream(date_from, date_to, event_type),
            "ai_results": lambda: self.export_ai_analysis_stream(date_from, date_to),
            "downlink": lambda: self.export_downlink_stream(date_from, date_to),
            "sessions": lambda: self.export_sessions_stream(date_from, date_to),
        }

        for export_type in types:
            if export_type not in exporters:
                continue
            async for record in exporters[export_type]():
                buf = io.StringIO()
                writer = csv.writer(buf)
                writer.writerow([export_type, json.dumps(record, default=str)])
                yield buf.getvalue()


export_service = ExportService()
