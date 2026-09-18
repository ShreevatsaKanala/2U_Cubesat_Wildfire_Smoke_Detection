"""Mission replay service — session management and playback control."""
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

from app.core.database import get_db
from app.services.persistence_service import persistence_service

logger = logging.getLogger(__name__)


@dataclass
class Session:
    session_id: str
    start_time: str
    end_time: Optional[str] = None
    config_snapshot: Optional[dict] = None
    total_observations: int = 0
    total_events: int = 0


@dataclass
class ReplayState:
    session_id: Optional[str] = None
    is_playing: bool = False
    speed: float = 1.0
    current_offset: float = 0.0
    total_duration: float = 0.0
    start_time: Optional[float] = None


class ReplayService:
    """Manages mission sessions and replay playback."""

    def __init__(self):
        self._replay_state = ReplayState()
        self._playback_task: Optional[asyncio.Task] = None
        self._sessions: dict[str, Session] = {}

    @property
    def replay_state(self) -> dict:
        return {
            "session_id": self._replay_state.session_id,
            "is_playing": self._replay_state.is_playing,
            "speed": self._replay_state.speed,
            "current_offset": round(self._replay_state.current_offset, 2),
            "total_duration": round(self._replay_state.total_duration, 2),
        }

    async def start_session(self, config: Optional[dict] = None) -> Session:
        if self._replay_state.session_id and self._replay_state.is_playing:
            await self.stop_session()

        session_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        session = Session(
            session_id=session_id,
            start_time=now,
            config_snapshot=config or {},
        )
        self._sessions[session_id] = session

        await persistence_service.save_session({
            "session_id": session_id,
            "start_time": now,
            "total_observations": 0,
            "total_events": 0,
            "config_snapshot": config,
        })

        logger.info(f"Started mission session: {session_id}")
        return session

    async def stop_session(self) -> Optional[Session]:
        if self._replay_state.is_playing:
            await self.pause()

        session_id = self._replay_state.session_id
        if not session_id:
            return None

        now = datetime.utcnow().isoformat()
        session = self._sessions.get(session_id)
        if session:
            session.end_time = now

        obs_count = await self._count_records("observations", session_id)
        event_count = await self._count_records("events", session_id)

        await persistence_service.save_session({
            "session_id": session_id,
            "start_time": session.start_time if session else now,
            "end_time": now,
            "total_observations": obs_count,
            "total_events": event_count,
            "config_snapshot": session.config_snapshot if session else None,
        })

        self._replay_state.session_id = None
        self._replay_state.current_offset = 0.0
        logger.info(f"Stopped mission session: {session_id}")
        return session

    async def list_sessions(self) -> list[dict]:
        db = await get_db()
        cursor = await db.execute(
            "SELECT * FROM mission_sessions ORDER BY start_time DESC"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_session(self, session_id: str) -> Optional[dict]:
        db = await get_db()
        cursor = await db.execute(
            "SELECT * FROM mission_sessions WHERE session_id = ?", (session_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_session_telemetry(self, session_id: str, limit: int = 1000) -> list[dict]:
        session = await self.get_session(session_id)
        if not session:
            return []
        return await persistence_service.get_telemetry(
            limit=limit,
            date_from=session.get("start_time"),
            date_to=session.get("end_time"),
        )

    async def get_session_observations(self, session_id: str, limit: int = 1000) -> list[dict]:
        session = await self.get_session(session_id)
        if not session:
            return []
        return await persistence_service.get_observations(
            limit=limit,
            date_from=session.get("start_time"),
            date_to=session.get("end_time"),
        )

    async def get_session_events(self, session_id: str, limit: int = 1000) -> list[dict]:
        session = await self.get_session(session_id)
        if not session:
            return []
        return await persistence_service.get_events(
            limit=limit,
            date_from=session.get("start_time"),
            date_to=session.get("end_time"),
        )

    async def start_playback(self, session_id: str, speed: float = 1.0) -> dict:
        if self._replay_state.is_playing:
            await self.pause()

        self._replay_state.session_id = session_id
        self._replay_state.speed = speed
        self._replay_state.current_offset = 0.0

        session = await self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}

        start = session.get("start_time")
        end = session.get("end_time")
        if start and end:
            try:
                s = datetime.fromisoformat(start)
                e = datetime.fromisoformat(end)
                self._replay_state.total_duration = (e - s).total_seconds()
            except (ValueError, TypeError):
                self._replay_state.total_duration = 0.0

        self._replay_state.is_playing = True
        self._replay_state.start_time = asyncio.get_event_loop().time()

        self._playback_task = asyncio.create_task(self._playback_loop())
        return self.replay_state

    async def pause(self) -> dict:
        self._replay_state.is_playing = False
        if self._playback_task and not self._playback_task.done():
            self._playback_task.cancel()
            try:
                await self._playback_task
            except asyncio.CancelledError:
                pass
        return self.replay_state

    async def seek(self, offset: float) -> dict:
        self._replay_state.current_offset = max(0.0, min(offset, self._replay_state.total_duration))
        if self._replay_state.is_playing:
            self._replay_state.start_time = asyncio.get_event_loop().time() - (
                self._replay_state.current_offset / self._replay_state.speed
            )
        return self.replay_state

    async def _playback_loop(self):
        try:
            while self._replay_state.is_playing:
                if self._replay_state.start_time is not None:
                    elapsed = asyncio.get_event_loop().time() - self._replay_state.start_time
                    self._replay_state.current_offset = elapsed * self._replay_state.speed

                    if self._replay_state.current_offset >= self._replay_state.total_duration:
                        self._replay_state.current_offset = self._replay_state.total_duration
                        self._replay_state.is_playing = False
                        break

                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass

    async def _count_records(self, table: str, session_id: str) -> int:
        session = await self.get_session(session_id)
        if not session:
            return 0
        db = await get_db()
        try:
            cursor = await db.execute(
                f"SELECT COUNT(*) FROM {table} WHERE timestamp >= ? AND timestamp <= ?",
                (session.get("start_time"), session.get("end_time")),
            )
            row = await cursor.fetchone()
            return row[0] if row else 0
        except Exception as e:
            logger.error(f"Failed to count {table}: {e}")
            return 0


replay_service = ReplayService()
