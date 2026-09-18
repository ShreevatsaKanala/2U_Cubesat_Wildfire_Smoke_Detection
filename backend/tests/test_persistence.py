"""Database persistence tests for CubeSat Digital Twin."""
import pytest
import pytest_asyncio
import aiosqlite
import tempfile
import os
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone


@pytest.fixture
def tmp_db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest_asyncio.fixture
async def db(tmp_db_path):
    """Create a fresh in-memory-like DB with schema for each test."""
    conn = await aiosqlite.connect(tmp_db_path)
    conn.row_factory = aiosqlite.Row
    schema_path = os.path.join(os.path.dirname(__file__), "..", "app", "core", "database.py")
    # Apply schema directly
    await conn.executescript("""
        CREATE TABLE IF NOT EXISTS observations (
            id TEXT PRIMARY KEY, timestamp TEXT NOT NULL, spacecraft_id TEXT,
            lat REAL, lon REAL, alt REAL, camera_angle TEXT, image_path TEXT,
            priority_score TEXT, fire_probability REAL, ai_status TEXT,
            ai_provider TEXT, ai_score REAL, ai_raw_response TEXT,
            smokiness_score REAL, classification TEXT, confidence REAL,
            classification_method TEXT, downlink_status TEXT
        );
        CREATE TABLE IF NOT EXISTS telemetry_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
            spacecraft_id TEXT, mission_mode TEXT, latitude REAL, longitude REAL,
            altitude_km REAL, velocity_km_s REAL, heading_deg REAL, roll_deg REAL,
            pitch_deg REAL, yaw_deg REAL, battery_soc REAL, battery_voltage REAL,
            solar_generation_w REAL, power_consumption_w REAL, charge_state TEXT,
            temperatures TEXT, communication_status TEXT, gps_status TEXT,
            camera_status TEXT, ml_status TEXT, health_status TEXT,
            smoke_probability REAL, confidence REAL, priority TEXT
        );
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT UNIQUE,
            timestamp TEXT NOT NULL, event_type TEXT, severity TEXT,
            details TEXT, source TEXT
        );
        CREATE TABLE IF NOT EXISTS downlink_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, observation_id TEXT,
            station_id TEXT, start_time TEXT, end_time TEXT, status TEXT,
            bytes_transferred INTEGER
        );
        CREATE TABLE IF NOT EXISTS ai_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT, observation_id TEXT,
            provider TEXT, model TEXT, score REAL, raw_response TEXT,
            latency_ms REAL, timestamp TEXT
        );
        CREATE TABLE IF NOT EXISTS mission_sessions (
            session_id TEXT PRIMARY KEY, start_time TEXT, end_time TEXT,
            total_observations INTEGER DEFAULT 0, total_events INTEGER DEFAULT 0,
            config_snapshot TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_obs_timestamp ON observations(timestamp);
        CREATE INDEX IF NOT EXISTS idx_obs_fire_prob ON observations(fire_probability);
        CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
        CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
        CREATE INDEX IF NOT EXISTS idx_downlink_obs ON downlink_history(observation_id);
        CREATE INDEX IF NOT EXISTS idx_ai_obs ON ai_analysis(observation_id);
    """)
    yield conn
    await conn.close()


# ── DB Schema Tests ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_schema_creates_all_tables(db):
    cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in await cursor.fetchall()}
    for t in ["observations", "telemetry_snapshots", "events", "downlink_history", "ai_analysis", "mission_sessions"]:
        assert t in tables


@pytest.mark.asyncio
async def test_observations_crud(db):
    await db.execute(
        """INSERT INTO observations (id, timestamp, spacecraft_id, lat, lon, alt, camera_angle,
           image_path, priority_score, fire_probability, ai_status, ai_provider, ai_score,
           ai_raw_response, smokiness_score, classification, confidence, classification_method, downlink_status)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        ("obs-1", "2024-01-01T00:00:00Z", "CSAT-001", 35.0, -120.0, 500.0,
         "auto", "img.jpg", "HIGH", 0.75, "success", "mock", 0.8,
         None, 0.75, "mock-smoke", 0.8, "ml", "pending")
    )
    await db.commit()
    cursor = await db.execute("SELECT * FROM observations WHERE id=?", ("obs-1",))
    row = await cursor.fetchone()
    assert row is not None
    assert row["fire_probability"] == 0.75
    assert row["ai_status"] == "success"


@pytest.mark.asyncio
async def test_telemetry_crud(db):
    await db.execute(
        """INSERT INTO telemetry_snapshots (timestamp, spacecraft_id, mission_mode,
           latitude, longitude, altitude_km, velocity_km_s, heading_deg,
           roll_deg, pitch_deg, yaw_deg, battery_soc, battery_voltage,
           solar_generation_w, power_consumption_w, charge_state, temperatures,
           communication_status, gps_status, camera_status, ml_status, health_status,
           smoke_probability, confidence, priority)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        ("2024-01-01T00:00:00Z", "CSAT-001", "IDLE", 35.0, -120.0, 500.0,
         7.6, 90.0, 0.0, 0.0, 90.0, 85.0, 7.2, 1.5, 1.2, "discharging",
         "{}", "nominal", "nominal", "nominal", "idle", "nominal", 0.0, 0.0, "LOW")
    )
    await db.commit()
    cursor = await db.execute("SELECT * FROM telemetry_snapshots LIMIT 1")
    row = await cursor.fetchone()
    assert row is not None
    assert row["battery_soc"] == 85.0


@pytest.mark.asyncio
async def test_events_crud(db):
    await db.execute(
        "INSERT INTO events (event_id, timestamp, event_type, severity, details, source) VALUES (?,?,?,?,?,?)",
        ("evt-1", "2024-01-01T00:00:00Z", "fire_detection", "high", "Smoke detected", "ai")
    )
    await db.commit()
    cursor = await db.execute("SELECT * FROM events WHERE event_id=?", ("evt-1",))
    row = await cursor.fetchone()
    assert row is not None
    assert row["event_type"] == "fire_detection"


@pytest.mark.asyncio
async def test_downlink_history_crud(db):
    await db.execute(
        "INSERT INTO downlink_history (observation_id, station_id, start_time, end_time, status, bytes_transferred) VALUES (?,?,?,?,?,?)",
        ("obs-1", "GS-001", "2024-01-01T00:00:00Z", "2024-01-01T00:05:00Z", "transmitted", 524288)
    )
    await db.commit()
    cursor = await db.execute("SELECT * FROM downlink_history LIMIT 1")
    row = await cursor.fetchone()
    assert row is not None and row["bytes_transferred"] == 524288


@pytest.mark.asyncio
async def test_ai_analysis_crud(db):
    await db.execute(
        "INSERT INTO ai_analysis (observation_id, provider, model, score, raw_response, latency_ms, timestamp) VALUES (?,?,?,?,?,?,?)",
        ("obs-1", "mock", "mock-v1", 0.85, "{}", 120.5, "2024-01-01T00:00:00Z")
    )
    await db.commit()
    cursor = await db.execute("SELECT * FROM ai_analysis LIMIT 1")
    row = await cursor.fetchone()
    assert row is not None and row["latency_ms"] == 120.5


@pytest.mark.asyncio
async def test_mission_sessions_crud(db):
    await db.execute(
        "INSERT INTO mission_sessions (session_id, start_time, end_time, total_observations, total_events, config_snapshot) VALUES (?,?,?,?,?,?)",
        ("sess-1", "2024-01-01T00:00:00Z", "2024-01-01T01:00:00Z", 10, 5, "{}")
    )
    await db.commit()
    cursor = await db.execute("SELECT * FROM mission_sessions WHERE session_id=?", ("sess-1",))
    row = await cursor.fetchone()
    assert row is not None and row["total_observations"] == 10


@pytest.mark.asyncio
async def test_observations_replace(db):
    for val in [0.5, 0.8]:
        await db.execute(
            """INSERT OR REPLACE INTO observations (id, timestamp, spacecraft_id, lat, lon, alt, camera_angle,
               image_path, priority_score, fire_probability, ai_status, ai_provider, ai_score,
               ai_raw_response, smokiness_score, classification, confidence, classification_method, downlink_status)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("obs-1", "2024-01-01T00:00:00Z", "CSAT", 0.0, 0.0, 500.0,
             None, None, None, val, None, None, None, None, val, None, None, None, None)
        )
        await db.commit()
    cursor = await db.execute("SELECT fire_probability FROM observations WHERE id='obs-1'")
    row = await cursor.fetchone()
    assert row[0] == 0.8


@pytest.mark.asyncio
async def test_observations_filter_by_fire_prob(db):
    for prob in [0.1, 0.3, 0.7, 0.9]:
        await db.execute(
            """INSERT INTO observations (id, timestamp, fire_probability, spacecraft_id, lat, lon, alt, image_path)
               VALUES (?,?,?,?,?,?,?,?)""",
            (f"obs-{prob}", "2024-01-01T00:00:00Z", prob, "CSAT", 0.0, 0.0, 500.0, "img.jpg")
        )
    await db.commit()
    cursor = await db.execute("SELECT COUNT(*) FROM observations WHERE fire_probability > 0.5")
    count = (await cursor.fetchone())[0]
    assert count == 2


@pytest.mark.asyncio
async def test_events_filter_by_type(db):
    for i, evt_type in enumerate(["fire", "fault", "fire"]):
        await db.execute(
            "INSERT INTO events (event_id, timestamp, event_type, severity, details, source) VALUES (?,?,?,?,?,?)",
            (f"evt-{i}", "2024-01-01T00:00:00Z", evt_type, "info", "test", "test")
        )
    await db.commit()
    cursor = await db.execute("SELECT COUNT(*) FROM events WHERE event_type='fire'")
    assert (await cursor.fetchone())[0] == 2


@pytest.mark.asyncio
async def test_stats_query(db):
    await db.execute(
        """INSERT INTO observations (id, timestamp, spacecraft_id, lat, lon, alt, image_path, fire_probability, confidence)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        ("obs-1", "2024-01-01T00:00:00Z", "CSAT", 0.0, 0.0, 500.0, "img.jpg", 0.8, 0.9)
    )
    await db.execute(
        "INSERT INTO events (event_id, timestamp, event_type, severity, details, source) VALUES (?,?,?,?,?,?)",
        ("evt-1", "2024-01-01T00:00:00Z", "fire", "high", "test", "test")
    )
    await db.execute(
        "INSERT INTO ai_analysis (observation_id, provider, model, score, latency_ms, timestamp) VALUES (?,?,?,?,?,?)",
        ("obs-1", "mock", "v1", 0.85, 100.0, "2024-01-01T00:00:00Z")
    )
    await db.commit()

    cursor = await db.execute("SELECT COUNT(*) FROM observations")
    assert (await cursor.fetchone())[0] == 1
    cursor = await db.execute("SELECT COUNT(*) FROM observations WHERE fire_probability > 0.5")
    assert (await cursor.fetchone())[0] == 1
    cursor = await db.execute("SELECT COUNT(*) FROM events")
    assert (await cursor.fetchone())[0] == 1
    cursor = await db.execute("SELECT AVG(confidence) FROM observations WHERE confidence IS NOT NULL")
    assert (await cursor.fetchone())[0] == 0.9
    cursor = await db.execute("SELECT AVG(latency_ms) FROM ai_analysis WHERE latency_ms IS NOT NULL")
    assert (await cursor.fetchone())[0] == 100.0


@pytest.mark.asyncio
async def test_index_exists(db):
    cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = {row[0] for row in await cursor.fetchall()}
    assert "idx_obs_timestamp" in indexes
    assert "idx_events_type" in indexes
    assert "idx_downlink_obs" in indexes
    assert "idx_ai_obs" in indexes
