"""Redis cache helpers for position data and CDM hot cache."""
import json
import logging
from typing import Optional

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

_redis: Optional[aioredis.Redis] = None

POSITIONS_KEY = "orbitalwatch:positions"
CDM_HOT_KEY = "orbitalwatch:cdm_hot"
STATS_KEY = "orbitalwatch:stats"
LAST_TLE_UPDATE_KEY = "orbitalwatch:last_tle_update"
LAST_CDM_UPDATE_KEY = "orbitalwatch:last_cdm_update"

# TTLs in seconds
POSITION_TTL = 120  # 2 minutes
CDM_TTL = 3600      # 1 hour
STATS_TTL = 300     # 5 minutes


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def cache_positions(positions: list[dict]) -> None:
    r = await get_redis()
    await r.set(POSITIONS_KEY, json.dumps(positions), ex=POSITION_TTL)


async def get_cached_positions() -> Optional[list[dict]]:
    r = await get_redis()
    data = await r.get(POSITIONS_KEY)
    if data:
        return json.loads(data)
    return None


async def cache_cdm_hot(conjunctions: list[dict]) -> None:
    r = await get_redis()
    await r.set(CDM_HOT_KEY, json.dumps(conjunctions), ex=CDM_TTL)


async def get_cached_cdm_hot() -> Optional[list[dict]]:
    r = await get_redis()
    data = await r.get(CDM_HOT_KEY)
    if data:
        return json.loads(data)
    return None


async def cache_stats(stats: dict) -> None:
    r = await get_redis()
    await r.set(STATS_KEY, json.dumps(stats, default=str), ex=STATS_TTL)


async def get_cached_stats() -> Optional[dict]:
    r = await get_redis()
    data = await r.get(STATS_KEY)
    if data:
        return json.loads(data)
    return None


async def set_last_update(key: str) -> None:
    r = await get_redis()
    from datetime import datetime, timezone
    await r.set(key, datetime.now(timezone.utc).isoformat())
    # Invalidate stats cache so fresh data shows immediately
    await r.delete(STATS_KEY)


async def get_last_update(key: str) -> Optional[str]:
    r = await get_redis()
    return await r.get(key)
