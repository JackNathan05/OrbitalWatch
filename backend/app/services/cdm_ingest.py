"""Space-Track.org CDM ingestion service.

Uses the Space-Track REST API directly (not the spacetrack library)
since the library's predicate validation doesn't match the CDM_PUBLIC class.

CDM_PUBLIC fields: CDM_ID, CREATED, EMERGENCY_REPORTABLE, TCA, MIN_RNG, PC,
  SAT_1_ID, SAT_1_NAME, SAT1_OBJECT_TYPE, SAT1_RCS, SAT_1_EXCL_VOL,
  SAT_2_ID, SAT_2_NAME, SAT2_OBJECT_TYPE, SAT2_RCS, SAT_2_EXCL_VOL
"""
import json
import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = logging.getLogger(__name__)

SPACETRACK_LOGIN_URL = "https://www.space-track.org/ajaxauth/login"
SPACETRACK_CDM_URL = (
    "https://www.space-track.org/basicspacedata/query"
    "/class/cdm_public"
)


async def fetch_cdm_data(days_ahead: int = 7, min_pc: float = 1e-6) -> list[dict]:
    """Fetch CDMs from Space-Track.org REST API directly."""
    now = datetime.now(timezone.utc)
    tca_start = now.strftime("%Y-%m-%d")
    tca_end = (now + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    url = (
        f"{SPACETRACK_CDM_URL}"
        f"/TCA/{tca_start}--{tca_end}"
        f"/PC/>{min_pc}"
        f"/orderby/PC desc"
        f"/limit/1000"
        f"/format/json"
    )

    async with httpx.AsyncClient(timeout=120.0) as client:
        # Authenticate
        login_resp = await client.post(
            SPACETRACK_LOGIN_URL,
            data={
                "identity": settings.spacetrack_username,
                "password": settings.spacetrack_password,
            },
        )
        login_resp.raise_for_status()

        # Fetch CDMs
        resp = await client.get(url)
        resp.raise_for_status()

        cdms = resp.json()
        logger.info(f"Fetched {len(cdms)} CDMs from Space-Track.org")
        return cdms


async def ingest_cdm_data(session: AsyncSession, cdm_records: list[dict]) -> int:
    """Upsert CDM records into the database.

    Maps CDM_PUBLIC fields to our schema:
      CDM_ID           -> cdm_id
      TCA              -> tca
      MIN_RNG          -> miss_distance_m (in km, converted to meters)
      PC               -> collision_probability
      SAT_1_ID         -> sat1_norad_id
      SAT_1_NAME       -> sat1_object_name
      SAT1_OBJECT_TYPE -> sat1_object_type
      SAT_2_ID         -> sat2_norad_id
      SAT_2_NAME       -> sat2_object_name
      SAT2_OBJECT_TYPE -> sat2_object_type
      CREATED          -> creation_date
    """
    if not cdm_records:
        return 0

    if cdm_records:
        logger.info(f"Sample CDM keys: {list(cdm_records[0].keys())}")

    count = 0
    for record in cdm_records:
        cdm_id = record.get("CDM_ID")
        if not cdm_id:
            continue

        tca_str = record.get("TCA", "")
        created_str = record.get("CREATED", "")
        try:
            tca = datetime.fromisoformat(tca_str.replace("Z", "+00:00"))
            creation_date = (
                datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                if created_str else tca
            )
        except (ValueError, AttributeError):
            continue

        sat1_id = record.get("SAT_1_ID")
        sat2_id = record.get("SAT_2_ID")
        if not sat1_id or not sat2_id:
            continue

        pc = record.get("PC")
        if pc is None:
            continue

        min_rng = record.get("MIN_RNG")
        miss_distance_m = float(min_rng) * 1000.0 if min_rng else 0.0

        await session.execute(
            text("""
                INSERT INTO cdm (
                    cdm_id, tca, sat1_norad_id, sat1_object_name, sat1_object_type,
                    sat2_norad_id, sat2_object_name, sat2_object_type,
                    miss_distance_m, collision_probability, relative_speed_ms,
                    creation_date, raw_json, ingested_at
                ) VALUES (
                    :cdm_id, :tca, :sat1_norad_id, :sat1_object_name, :sat1_object_type,
                    :sat2_norad_id, :sat2_object_name, :sat2_object_type,
                    :miss_distance_m, :collision_probability, :relative_speed_ms,
                    :creation_date, :raw_json, :ingested_at
                ) ON CONFLICT (cdm_id) DO UPDATE SET
                    miss_distance_m = EXCLUDED.miss_distance_m,
                    collision_probability = EXCLUDED.collision_probability,
                    relative_speed_ms = EXCLUDED.relative_speed_ms,
                    creation_date = EXCLUDED.creation_date,
                    raw_json = EXCLUDED.raw_json,
                    ingested_at = EXCLUDED.ingested_at
            """),
            {
                "cdm_id": str(cdm_id),
                "tca": tca,
                "sat1_norad_id": int(sat1_id),
                "sat1_object_name": record.get("SAT_1_NAME"),
                "sat1_object_type": record.get("SAT1_OBJECT_TYPE"),
                "sat2_norad_id": int(sat2_id),
                "sat2_object_name": record.get("SAT_2_NAME"),
                "sat2_object_type": record.get("SAT2_OBJECT_TYPE"),
                "miss_distance_m": miss_distance_m,
                "collision_probability": float(pc),
                "relative_speed_ms": None,
                "creation_date": creation_date,
                "raw_json": json.dumps(record),
                "ingested_at": datetime.now(timezone.utc),
            }
        )
        count += 1

    await session.commit()
    logger.info(f"Upserted {count} CDM records into database")
    return count
