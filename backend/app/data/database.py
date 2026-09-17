import logging

logger = logging.getLogger(__name__)


async def init_db() -> None:
    logger.info("Database initialization (Phase 1: in-memory storage via ObservationService)")


async def get_db():
    yield None
