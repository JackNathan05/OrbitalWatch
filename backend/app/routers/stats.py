"""Platform statistics endpoint."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import PlatformStats, ConjunctionSummary
from app.services.cache import (
    get_cached_stats, cache_stats,
    get_last_update, LAST_TLE_UPDATE_KEY, LAST_CDM_UPDATE_KEY,
)

router = APIRouter(tags=["stats"])


@router.get("/stats", response_model=PlatformStats)
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Object count, active conjunctions (7d), high-risk count, and data freshness timestamps."""
    # Try cache
    cached = await get_cached_stats()
    if cached:
        return PlatformStats(**cached)

    now = datetime.now(timezone.utc)
    week_ahead = now + timedelta(days=7)

    # Total objects tracked
    total_result = await db.execute(text("SELECT COUNT(*) FROM gp_elements"))
    total_objects = total_result.scalar() or 0

    # Active conjunctions in next 7 days with Pc > 1e-5
    active_result = await db.execute(
        text("""
            SELECT COUNT(*) FROM cdm
            WHERE tca >= :now AND tca <= :week_ahead
              AND collision_probability >= 1e-5
        """),
        {"now": now, "week_ahead": week_ahead}
    )
    active_conjunctions = active_result.scalar() or 0

    # High risk events (Pc > 1e-3)
    high_risk_result = await db.execute(
        text("""
            SELECT COUNT(*) FROM cdm
            WHERE tca >= :now AND tca <= :week_ahead
              AND collision_probability >= 1e-3
        """),
        {"now": now, "week_ahead": week_ahead}
    )
    high_risk_events = high_risk_result.scalar() or 0

    # Most recent high-risk event
    most_recent_result = await db.execute(
        text("""
            SELECT cdm_id, tca, sat1_norad_id, sat1_object_name, sat1_object_type,
                   sat2_norad_id, sat2_object_name, sat2_object_type,
                   miss_distance_m, collision_probability, relative_speed_ms
            FROM cdm
            WHERE collision_probability >= 1e-3
            ORDER BY creation_date DESC
            LIMIT 1
        """)
    )
    most_recent_row = most_recent_result.fetchone()
    most_recent_high_risk = None
    if most_recent_row:
        from app.routers.conjunctions import _risk_level
        most_recent_high_risk = ConjunctionSummary(
            cdm_id=most_recent_row.cdm_id,
            tca=most_recent_row.tca,
            sat1_norad_id=most_recent_row.sat1_norad_id,
            sat1_object_name=most_recent_row.sat1_object_name,
            sat1_object_type=most_recent_row.sat1_object_type,
            sat2_norad_id=most_recent_row.sat2_norad_id,
            sat2_object_name=most_recent_row.sat2_object_name,
            sat2_object_type=most_recent_row.sat2_object_type,
            miss_distance_m=most_recent_row.miss_distance_m,
            collision_probability=most_recent_row.collision_probability,
            relative_speed_ms=most_recent_row.relative_speed_ms,
            risk_level=_risk_level(most_recent_row.collision_probability),
        )

    # Data freshness
    last_tle = await get_last_update(LAST_TLE_UPDATE_KEY)
    last_cdm = await get_last_update(LAST_CDM_UPDATE_KEY)

    stats = PlatformStats(
        total_objects_tracked=total_objects,
        active_conjunctions_7d=active_conjunctions,
        high_risk_events=high_risk_events,
        most_recent_high_risk=most_recent_high_risk,
        last_tle_update=datetime.fromisoformat(last_tle) if last_tle else None,
        last_cdm_update=datetime.fromisoformat(last_cdm) if last_cdm else None,
    )

    await cache_stats(stats.model_dump())
    return stats
