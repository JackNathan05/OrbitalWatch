"""Celery tasks for periodic data ingestion and position pre-computation."""
import asyncio
import json
import logging
from datetime import datetime, timezone

from app.tasks.celery_app import celery_app
from app.config import settings

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async function from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.tasks.ingestion.ingest_tles")
def ingest_tles():
    """Fetch and ingest TLE/GP data from CelesTrak."""
    async def _ingest():
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
        from app.services.tle_ingest import run_full_ingestion
        from app.services.cache import set_last_update, LAST_TLE_UPDATE_KEY

        engine = create_async_engine(settings.database_url)
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with session_factory() as session:
            count = await run_full_ingestion(session)
            await set_last_update(LAST_TLE_UPDATE_KEY)
            logger.info(f"TLE ingestion complete: {count} records")

        await engine.dispose()
        return count

    return _run_async(_ingest())


@celery_app.task(name="app.tasks.ingestion.ingest_cdms")
def ingest_cdms():
    """Fetch and ingest CDM data from Space-Track.org."""
    async def _ingest():
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
        from app.services.cdm_ingest import fetch_cdm_data, ingest_cdm_data
        from app.services.cache import set_last_update, LAST_CDM_UPDATE_KEY

        cdm_records = await fetch_cdm_data(days_ahead=7, min_pc=1e-6)

        engine = create_async_engine(settings.database_url)
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with session_factory() as session:
            count = await ingest_cdm_data(session, cdm_records)
            await set_last_update(LAST_CDM_UPDATE_KEY)
            logger.info(f"CDM ingestion complete: {count} records")

        await engine.dispose()
        return count

    return _run_async(_ingest())


@celery_app.task(name="app.tasks.ingestion.precompute_positions")
def precompute_positions():
    """Pre-compute positions for all tracked satellites and cache in Redis."""
    async def _compute():
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
        from sqlalchemy import text
        from app.services.propagator import propagate_tle, propagate_omm
        from app.services.cache import cache_positions

        engine = create_async_engine(settings.database_url)
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT norad_cat_id, object_name, object_type,
                           tle_line1, tle_line2,
                           epoch, mean_motion, eccentricity, inclination,
                           ra_of_asc_node, arg_of_pericenter, mean_anomaly, bstar
                    FROM gp_elements
                    WHERE mean_motion IS NOT NULL AND mean_motion > 0
                    ORDER BY norad_cat_id
                    LIMIT 5000
                """)
            )
            rows = result.fetchall()

        positions = []
        now = datetime.now(timezone.utc)
        for row in rows:
            pos = None
            if row.tle_line1 and row.tle_line2:
                pos = propagate_tle(row.tle_line1, row.tle_line2, now)
            if pos is None and row.mean_motion and row.epoch:
                epoch = row.epoch if row.epoch.tzinfo else row.epoch.replace(tzinfo=timezone.utc)
                pos = propagate_omm(
                    norad_id=row.norad_cat_id, epoch=epoch,
                    mean_motion=row.mean_motion, eccentricity=row.eccentricity or 0.0,
                    inclination=row.inclination or 0.0, ra_of_asc_node=row.ra_of_asc_node or 0.0,
                    arg_of_pericenter=row.arg_of_pericenter or 0.0,
                    mean_anomaly=row.mean_anomaly or 0.0, bstar=row.bstar or 0.0, dt=now,
                )
            if pos:
                lat, lon, alt = pos
                positions.append({
                    "norad_cat_id": row.norad_cat_id,
                    "object_name": row.object_name,
                    "object_type": row.object_type,
                    "latitude": round(lat, 4),
                    "longitude": round(lon, 4),
                    "altitude_km": round(alt, 2),
                })

        await cache_positions(positions)
        await engine.dispose()
        logger.info(f"Pre-computed {len(positions)} satellite positions")
        return len(positions)

    return _run_async(_compute())
