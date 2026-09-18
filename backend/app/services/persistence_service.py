"""Persistence service for simulation state — reads/writes to SQLite."""
import json
import logging
from datetime import datetime
from typing import Optional

from app.core.database import get_db

logger = logging.getLogger(__name__)


class PersistenceService:
    """Thin async wrapper around SQLite for persisting simulation artifacts."""

    # ── Observations ────────────────────────────────────────────────
    async def save_observation(self, obs: dict) -> None:
        try:
            db = await get_db()
            await db.execute(
                """INSERT OR REPLACE INTO observations
                   (id, timestamp, spacecraft_id, lat, lon, alt, camera_angle,
                    image_path, priority_score, fire_probability, ai_status,
                    ai_provider, ai_score, ai_raw_response, smokiness_score,
                    classification, confidence, classification_method, downlink_status)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    obs.get("observation_id", obs.get("id")),
                    _ts(obs.get("timestamp")),
                    obs.get("spacecraft_id"),
                    obs.get("latitude", obs.get("lat")),
                    obs.get("longitude", obs.get("lon")),
                    obs.get("altitude_km", obs.get("alt")),
                    obs.get("capture_mode", obs.get("camera_angle")),
                    obs.get("image_path"),
                    obs.get("priority"),
                    obs.get("smoke_probability", obs.get("fire_probability")),
                    obs.get("ai_status"),
                    obs.get("ai_provider"),
                    obs.get("ai_smoke_score", obs.get("ai_score")),
                    _safe_json(obs.get("ai_raw_response")),
                    obs.get("smoke_probability", obs.get("smokiness_score")),
                    obs.get("model_name", obs.get("classification")),
                    obs.get("confidence"),
                    _classification_method(obs),
                    obs.get("downlink_status", "pending"),
                ),
            )
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to save observation: {e}")

    async def get_observations(
        self,
        limit: int = 50,
        offset: int = 0,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        min_fire_probability: Optional[float] = None,
        ai_status: Optional[str] = None,
    ) -> list[dict]:
        try:
            db = await get_db()
            where, params = [], []
            if date_from:
                where.append("timestamp >= ?")
                params.append(date_from)
            if date_to:
                where.append("timestamp <= ?")
                params.append(date_to)
            if min_fire_probability is not None:
                where.append("fire_probability >= ?")
                params.append(min_fire_probability)
            if ai_status:
                where.append("ai_status = ?")
                params.append(ai_status)
            clause = (" WHERE " + " AND ".join(where)) if where else ""
            sql = f"SELECT * FROM observations{clause} ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            cursor = await db.execute(sql, params)
            rows = await cursor.fetchall()
            return [_row_to_dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to query observations: {e}")
            return []

    async def count_observations(self) -> int:
        try:
            db = await get_db()
            cursor = await db.execute("SELECT COUNT(*) FROM observations")
            row = await cursor.fetchone()
            return row[0]
        except Exception:
            return 0

    # ── Telemetry snapshots ─────────────────────────────────────────
    async def save_telemetry(self, pkt: dict) -> None:
        try:
            db = await get_db()
            await db.execute(
                """INSERT INTO telemetry_snapshots
                   (timestamp, spacecraft_id, mission_mode, latitude, longitude,
                    altitude_km, velocity_km_s, heading_deg, roll_deg, pitch_deg,
                    yaw_deg, battery_soc, battery_voltage, solar_generation_w,
                    power_consumption_w, charge_state, temperatures,
                    communication_status, gps_status, camera_status, ml_status,
                    health_status, smoke_probability, confidence, priority)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    _ts(pkt.get("timestamp")),
                    pkt.get("spacecraft_id"),
                    pkt.get("mission_mode"),
                    pkt.get("latitude"),
                    pkt.get("longitude"),
                    pkt.get("altitude_km"),
                    pkt.get("velocity_km_s"),
                    pkt.get("heading_deg"),
                    pkt.get("roll_deg"),
                    pkt.get("pitch_deg"),
                    pkt.get("yaw_deg"),
                    pkt.get("battery_percentage", pkt.get("battery_soc")),
                    pkt.get("battery_voltage"),
                    pkt.get("power_generation_w", pkt.get("solar_generation_w")),
                    pkt.get("power_consumption_w"),
                    pkt.get("charge_state"),
                    _safe_json(pkt.get("temperatures")),
                    pkt.get("communication_status"),
                    pkt.get("gps_status"),
                    pkt.get("camera_status"),
                    pkt.get("ml_status"),
                    pkt.get("health_status"),
                    pkt.get("smoke_probability"),
                    pkt.get("confidence"),
                    pkt.get("priority"),
                ),
            )
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to save telemetry: {e}")

    async def get_telemetry(
        self,
        limit: int = 100,
        offset: int = 0,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> list[dict]:
        try:
            db = await get_db()
            where, params = [], []
            if date_from:
                where.append("timestamp >= ?")
                params.append(date_from)
            if date_to:
                where.append("timestamp <= ?")
                params.append(date_to)
            clause = (" WHERE " + " AND ".join(where)) if where else ""
            sql = f"SELECT * FROM telemetry_snapshots{clause} ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            cursor = await db.execute(sql, params)
            rows = await cursor.fetchall()
            return [_row_to_dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to query telemetry: {e}")
            return []

    # ── Events ──────────────────────────────────────────────────────
    async def save_event(self, event: dict) -> None:
        try:
            db = await get_db()
            await db.execute(
                """INSERT OR IGNORE INTO events
                   (event_id, timestamp, event_type, severity, details, source)
                   VALUES (?,?,?,?,?,?)""",
                (
                    event.get("event_id"),
                    _ts(event.get("timestamp")),
                    event.get("event_type", event.get("type")),
                    event.get("severity"),
                    event.get("description", event.get("details")),
                    event.get("subsystem", event.get("source")),
                ),
            )
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to save event: {e}")

    async def get_events(
        self,
        limit: int = 100,
        offset: int = 0,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> list[dict]:
        try:
            db = await get_db()
            where, params = [], []
            if event_type:
                where.append("event_type = ?")
                params.append(event_type)
            if severity:
                where.append("severity = ?")
                params.append(severity)
            if date_from:
                where.append("timestamp >= ?")
                params.append(date_from)
            if date_to:
                where.append("timestamp <= ?")
                params.append(date_to)
            clause = (" WHERE " + " AND ".join(where)) if where else ""
            sql = f"SELECT * FROM events{clause} ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            cursor = await db.execute(sql, params)
            rows = await cursor.fetchall()
            return [_row_to_dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to query events: {e}")
            return []

    # ── Downlink history ────────────────────────────────────────────
    async def save_downlink(self, record: dict) -> None:
        try:
            db = await get_db()
            await db.execute(
                """INSERT INTO downlink_history
                   (observation_id, station_id, start_time, end_time, status, bytes_transferred)
                   VALUES (?,?,?,?,?,?)""",
                (
                    record.get("observation_id"),
                    record.get("station_id"),
                    _ts(record.get("start_time")),
                    _ts(record.get("end_time")),
                    record.get("status"),
                    record.get("bytes_transferred", 0),
                ),
            )
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to save downlink record: {e}")

    # ── AI analysis ─────────────────────────────────────────────────
    async def save_ai_analysis(self, record: dict) -> None:
        try:
            db = await get_db()
            await db.execute(
                """INSERT INTO ai_analysis
                   (observation_id, provider, model, score, raw_response, latency_ms, timestamp)
                   VALUES (?,?,?,?,?,?,?)""",
                (
                    record.get("observation_id"),
                    record.get("provider"),
                    record.get("model"),
                    record.get("score"),
                    record.get("raw_response"),
                    record.get("latency_ms"),
                    _ts(record.get("timestamp")),
                ),
            )
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to save AI analysis: {e}")

    # ── Mission sessions ────────────────────────────────────────────
    async def save_session(self, session: dict) -> None:
        try:
            db = await get_db()
            await db.execute(
                """INSERT OR REPLACE INTO mission_sessions
                   (session_id, start_time, end_time, total_observations, total_events, config_snapshot)
                   VALUES (?,?,?,?,?,?)""",
                (
                    session.get("session_id"),
                    _ts(session.get("start_time")),
                    _ts(session.get("end_time")),
                    session.get("total_observations", 0),
                    session.get("total_events", 0),
                    _safe_json(session.get("config_snapshot")),
                ),
            )
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to save session: {e}")

    # ── Stats ───────────────────────────────────────────────────────
    async def get_stats(self) -> dict:
        try:
            db = await get_db()
            stats: dict = {}

            cursor = await db.execute("SELECT COUNT(*) FROM observations")
            stats["total_observations"] = (await cursor.fetchone())[0]

            cursor = await db.execute(
                "SELECT COUNT(*) FROM observations WHERE fire_probability > 0.5"
            )
            stats["fire_detections"] = (await cursor.fetchone())[0]

            cursor = await db.execute(
                "SELECT AVG(confidence) FROM observations WHERE confidence IS NOT NULL"
            )
            row = await cursor.fetchone()
            stats["avg_confidence"] = round(row[0], 4) if row[0] else 0.0

            cursor = await db.execute("SELECT COUNT(*) FROM events")
            stats["total_events"] = (await cursor.fetchone())[0]

            cursor = await db.execute("SELECT COUNT(*) FROM downlink_history WHERE status = 'transmitted'")
            stats["total_downlinks"] = (await cursor.fetchone())[0]

            cursor = await db.execute("SELECT COUNT(*) FROM ai_analysis")
            stats["total_ai_analyses"] = (await cursor.fetchone())[0]

            cursor = await db.execute(
                "SELECT AVG(latency_ms) FROM ai_analysis WHERE latency_ms IS NOT NULL"
            )
            row = await cursor.fetchone()
            stats["avg_ai_latency_ms"] = round(row[0], 2) if row[0] else 0.0

            return stats
        except Exception as e:
            logger.error(f"Failed to compute stats: {e}")
            return {}

    # ── Export ──────────────────────────────────────────────────────
    async def export_all(self) -> dict:
        try:
            return {
                "observations": await self.get_observations(limit=10000),
                "telemetry": await self.get_telemetry(limit=10000),
                "events": await self.get_events(limit=10000),
                "stats": await self.get_stats(),
            }
        except Exception as e:
            logger.error(f"Failed to export: {e}")
            return {}


# ── helpers ─────────────────────────────────────────────────────────

def _ts(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _safe_json(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value)
    except Exception:
        return str(value)


def _classification_method(obs: dict) -> str | None:
    if obs.get("model_name") and obs.get("ai_provider"):
        return "fusion"
    if obs.get("ai_provider"):
        return "ai"
    if obs.get("model_name"):
        return "ml"
    return None


def _row_to_dict(row) -> dict:
    if row is None:
        return {}
    return dict(row)


persistence_service = PersistenceService()
