"""CelesTrak TLE/GP ingestion service.

Fetches GP data in OMM/JSON format from CelesTrak (no auth required).
Supports 9-digit catalog numbers via JSON format.
"""
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import GPElement

logger = logging.getLogger(__name__)

CELESTRAK_GP_URL = f"{settings.celestrak_base_url}/NORAD/elements/gp.php"


async def fetch_gp_data(group: str = "active") -> list[dict]:
    """Fetch GP data from CelesTrak in JSON format.

    Groups: 'active', 'stations', 'visual', 'starlink', 'last-30-days', etc.
    Full catalog: group='active' returns ~8k active payloads.
    For all objects: use multiple group fetches.
    """
    params = {"GROUP": group, "FORMAT": "json"}

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.get(CELESTRAK_GP_URL, params=params)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Fetched {len(data)} GP records from CelesTrak (group={group})")
        return data


async def ingest_gp_data(session: AsyncSession, gp_records: list[dict]) -> int:
    """Upsert GP records into the database.

    Uses PostgreSQL ON CONFLICT for efficient upsert.
    Returns number of records processed.
    """
    if not gp_records:
        return 0

    count = 0
    for record in gp_records:
        norad_id = record.get("NORAD_CAT_ID")
        if not norad_id:
            continue

        epoch_str = record.get("EPOCH", "")
        try:
            epoch = datetime.fromisoformat(epoch_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue

        launch_date = None
        ld = record.get("LAUNCH_DATE")
        if ld:
            try:
                launch_date = datetime.strptime(ld, "%Y-%m-%d")
            except ValueError:
                pass

        await session.execute(
            text("""
                INSERT INTO gp_elements (
                    norad_cat_id, object_name, object_type, object_id,
                    country_code, launch_date, epoch, mean_motion,
                    eccentricity, inclination, ra_of_asc_node, arg_of_pericenter,
                    mean_anomaly, bstar, period_minutes, apogee_km, perigee_km,
                    tle_line1, tle_line2, ingested_at
                ) VALUES (
                    :norad_cat_id, :object_name, :object_type, :object_id,
                    :country_code, :launch_date, :epoch, :mean_motion,
                    :eccentricity, :inclination, :ra_of_asc_node, :arg_of_pericenter,
                    :mean_anomaly, :bstar, :period_minutes, :apogee_km, :perigee_km,
                    :tle_line1, :tle_line2, :ingested_at
                ) ON CONFLICT (norad_cat_id) DO UPDATE SET
                    object_name = EXCLUDED.object_name,
                    object_type = EXCLUDED.object_type,
                    epoch = EXCLUDED.epoch,
                    mean_motion = EXCLUDED.mean_motion,
                    eccentricity = EXCLUDED.eccentricity,
                    inclination = EXCLUDED.inclination,
                    ra_of_asc_node = EXCLUDED.ra_of_asc_node,
                    arg_of_pericenter = EXCLUDED.arg_of_pericenter,
                    mean_anomaly = EXCLUDED.mean_anomaly,
                    bstar = EXCLUDED.bstar,
                    period_minutes = EXCLUDED.period_minutes,
                    apogee_km = EXCLUDED.apogee_km,
                    perigee_km = EXCLUDED.perigee_km,
                    tle_line1 = EXCLUDED.tle_line1,
                    tle_line2 = EXCLUDED.tle_line2,
                    ingested_at = EXCLUDED.ingested_at
            """),
            {
                "norad_cat_id": int(norad_id),
                "object_name": record.get("OBJECT_NAME", "UNKNOWN"),
                "object_type": record.get("OBJECT_TYPE", "UNKNOWN"),
                "object_id": record.get("OBJECT_ID"),
                "country_code": record.get("COUNTRY_CODE"),
                "launch_date": launch_date,
                "epoch": epoch,
                "mean_motion": float(record.get("MEAN_MOTION", 0)),
                "eccentricity": float(record.get("ECCENTRICITY", 0)),
                "inclination": float(record.get("INCLINATION", 0)),
                "ra_of_asc_node": float(record.get("RA_OF_ASC_NODE", 0)),
                "arg_of_pericenter": float(record.get("ARG_OF_PERICENTER", 0)),
                "mean_anomaly": float(record.get("MEAN_ANOMALY", 0)),
                "bstar": float(record.get("BSTAR", 0)),
                "period_minutes": float(record.get("PERIOD", 0)) if record.get("PERIOD") else None,
                "apogee_km": float(record.get("APOAPSIS", 0)) if record.get("APOAPSIS") else None,
                "perigee_km": float(record.get("PERIAPSIS", 0)) if record.get("PERIAPSIS") else None,
                "tle_line1": record.get("TLE_LINE1"),
                "tle_line2": record.get("TLE_LINE2"),
                "ingested_at": datetime.now(timezone.utc),
            }
        )
        count += 1

    await session.commit()
    logger.info(f"Upserted {count} GP records into database")
    return count


async def run_full_ingestion(session: AsyncSession) -> int:
    """Run a full TLE ingestion from CelesTrak for key satellite groups."""
    groups = ["active", "stations", "visual", "analyst", "gpz", "gpz-plus"]
    total = 0
    for group in groups:
        try:
            records = await fetch_gp_data(group)
            count = await ingest_gp_data(session, records)
            total += count
        except Exception as e:
            logger.error(f"Failed to ingest group '{group}': {e}")
    return total
