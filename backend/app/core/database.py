"""Async SQLite database for simulation state persistence."""
import os
import aiosqlite
import logging

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "simulation.db")

_db: aiosqlite.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS observations (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    spacecraft_id TEXT,
    lat REAL,
    lon REAL,
    alt REAL,
    camera_angle TEXT,
    image_path TEXT,
    priority_score TEXT,
    fire_probability REAL,
    ai_status TEXT,
    ai_provider TEXT,
    ai_score REAL,
    ai_raw_response TEXT,
    smokiness_score REAL,
    classification TEXT,
    confidence REAL,
    classification_method TEXT,
    downlink_status TEXT
);

CREATE TABLE IF NOT EXISTS telemetry_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    spacecraft_id TEXT,
    mission_mode TEXT,
    latitude REAL,
    longitude REAL,
    altitude_km REAL,
    velocity_km_s REAL,
    heading_deg REAL,
    roll_deg REAL,
    pitch_deg REAL,
    yaw_deg REAL,
    battery_soc REAL,
    battery_voltage REAL,
    solar_generation_w REAL,
    power_consumption_w REAL,
    charge_state TEXT,
    temperatures TEXT,
    communication_status TEXT,
    gps_status TEXT,
    camera_status TEXT,
    ml_status TEXT,
    health_status TEXT,
    smoke_probability REAL,
    confidence REAL,
    priority TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE,
    timestamp TEXT NOT NULL,
    event_type TEXT,
    severity TEXT,
    details TEXT,
    source TEXT
);

CREATE TABLE IF NOT EXISTS downlink_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    observation_id TEXT,
    station_id TEXT,
    start_time TEXT,
    end_time TEXT,
    status TEXT,
    bytes_transferred INTEGER,
    FOREIGN KEY (observation_id) REFERENCES observations(id)
);

CREATE TABLE IF NOT EXISTS ai_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    observation_id TEXT,
    provider TEXT,
    model TEXT,
    score REAL,
    raw_response TEXT,
    latency_ms REAL,
    timestamp TEXT,
    FOREIGN KEY (observation_id) REFERENCES observations(id)
);

CREATE TABLE IF NOT EXISTS mission_sessions (
    session_id TEXT PRIMARY KEY,
    start_time TEXT,
    end_time TEXT,
    total_observations INTEGER DEFAULT 0,
    total_events INTEGER DEFAULT 0,
    config_snapshot TEXT
);

CREATE INDEX IF NOT EXISTS idx_obs_timestamp ON observations(timestamp);
CREATE INDEX IF NOT EXISTS idx_obs_fire_prob ON observations(fire_probability);
CREATE INDEX IF NOT EXISTS idx_obs_ai_status ON observations(ai_status);
CREATE INDEX IF NOT EXISTS idx_telem_timestamp ON telemetry_snapshots(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_downlink_obs ON downlink_history(observation_id);
CREATE INDEX IF NOT EXISTS idx_ai_obs ON ai_analysis(observation_id);
"""


async def init_db():
    """Initialize database: create directory, file, and tables."""
    global _db
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    _db = await aiosqlite.connect(DB_PATH)
    _db.row_factory = aiosqlite.Row
    await _db.executescript(SCHEMA)
    await _db.commit()
    logger.info(f"Database initialized at {DB_PATH}")


async def get_db() -> aiosqlite.Connection:
    """Get the shared database connection. Initializes if needed."""
    global _db
    if _db is None:
        await init_db()
    return _db


async def close_db():
    """Close the database connection."""
    global _db
    if _db:
        await _db.close()
        _db = None
