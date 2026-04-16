import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db, async_session
from app.routers import positions, conjunctions, satellites, stats

logger = logging.getLogger("orbitalwatch.scheduler")
logging.basicConfig(level=logging.INFO)


async def _refresh_tles():
    """Pull fresh TLEs from CelesTrak across multiple satellite groups."""
    from app.services.tle_ingest import fetch_gp_data, ingest_gp_data
    from app.services.cache import set_last_update, LAST_TLE_UPDATE_KEY

    groups = [
        "stations", "visual", "starlink", "oneweb", "planet", "spire",
        "geo", "resource", "science", "military", "cubesat", "weather",
        "noaa", "gps-ops", "galileo", "beidou", "iridium-NEXT",
        "globalstar", "amateur", "last-30-days",
    ]
    total = 0
    for group in groups:
        try:
            records = await fetch_gp_data(group)
            if not records:
                continue
            async with async_session() as session:
                count = await ingest_gp_data(session, records)
            total += count
            logger.info(f"TLE refresh: {count} from '{group}'")
            await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"TLE refresh failed for '{group}': {e}")
    if total > 0:
        await set_last_update(LAST_TLE_UPDATE_KEY)


async def _refresh_satcat():
    """Pull object types from Space-Track SATCAT."""
    from app.services.satcat_ingest import fetch_satcat_types, update_object_types

    if not settings.spacetrack_username or not settings.spacetrack_password:
        return
    try:
        records = await fetch_satcat_types()
        async with async_session() as session:
            count = await update_object_types(session, records)
        logger.info(f"SATCAT refresh: {count} types updated")
    except Exception as e:
        logger.error(f"SATCAT refresh failed: {e}")


async def _refresh_cdms():
    """Pull CDMs from Space-Track."""
    from app.services.cdm_ingest import fetch_cdm_data, ingest_cdm_data
    from app.services.cache import set_last_update, LAST_CDM_UPDATE_KEY

    if not settings.spacetrack_username or not settings.spacetrack_password:
        return
    try:
        cdms = await fetch_cdm_data(days_ahead=7, min_pc=1e-6)
        async with async_session() as session:
            count = await ingest_cdm_data(session, cdms)
        await set_last_update(LAST_CDM_UPDATE_KEY)
        logger.info(f"CDM refresh: {count} records")
    except Exception as e:
        logger.error(f"CDM refresh failed: {e}")


async def _precompute_positions():
    """Propagate orbits and cache lat/lon/alt in Redis."""
    from datetime import datetime, timezone
    from sqlalchemy import text
    from app.services.propagator import propagate_tle, propagate_omm
    from app.services.cache import cache_positions

    try:
        async with async_session() as session:
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

        now = datetime.now(timezone.utc)
        pos_list = []
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
                pos_list.append({
                    "norad_cat_id": row.norad_cat_id,
                    "object_name": row.object_name,
                    "object_type": row.object_type,
                    "latitude": round(lat, 4),
                    "longitude": round(lon, 4),
                    "altitude_km": round(alt, 2),
                })

        await cache_positions(pos_list)
        logger.info(f"Positions cached: {len(pos_list)} satellites")
    except Exception as e:
        logger.error(f"Position precompute failed: {e}")


async def scheduler():
    """Background loop. Positions every 60s, data refresh every 4h.

    start.bat handles the initial data load before this server starts,
    so this only does periodic maintenance.
    """
    REFRESH_INTERVAL = 4 * 3600   # 4 hours
    POSITION_INTERVAL = 60        # 60 seconds

    # Cache positions immediately on startup (data should already be in DB)
    await asyncio.sleep(2)
    await _precompute_positions()

    refresh_countdown = REFRESH_INTERVAL  # first data refresh in 4h

    while True:
        await asyncio.sleep(POSITION_INTERVAL)

        try:
            await _precompute_positions()

            if refresh_countdown <= 0:
                logger.info("Running scheduled data refresh...")
                await _refresh_tles()
                await _refresh_cdms()
                await _refresh_satcat()
                refresh_countdown = REFRESH_INTERVAL
                logger.info("Data refresh complete.")

            refresh_countdown -= POSITION_INTERVAL

        except Exception as e:
            logger.error(f"Scheduler error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    task = asyncio.create_task(scheduler())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="OrbitalWatch API",
    description="API for satellite positions, conjunction data (CDMs), and search. Data from CelesTrak and Space-Track.org.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(positions.router, prefix="/api")
app.include_router(conjunctions.router, prefix="/api")
app.include_router(satellites.router, prefix="/api")
app.include_router(stats.router, prefix="/api")


@app.get("/")
async def health_check():
    return {"status": "ok", "service": "orbitalwatch-api"}
