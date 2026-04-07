import os

import asyncpg
import structlog

logger = structlog.get_logger()

_pool: asyncpg.Pool | None = None

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS mcp_clipboard (
    id SERIAL PRIMARY KEY,
    source VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
"""


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        dsn = os.environ.get("DATABASE_URL")
        if not dsn:
            raise RuntimeError("DATABASE_URL is not set")
        _pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
        async with _pool.acquire() as conn:
            await conn.execute(_CREATE_TABLE)
        logger.info("db_pool_initialized")
    return _pool