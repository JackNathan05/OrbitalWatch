"""Space-Track SATCAT ingestion — fetches OBJECT_TYPE for all tracked satellites.

CelesTrak GP data doesn't include OBJECT_TYPE, so we pull it from
Space-Track's SATCAT (Satellite Catalog) and update our gp_elements table.
"""
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = logging.getLogger(__name__)

SPACETRACK_LOGIN_URL = "https://www.space-track.org/ajaxauth/login"
SPACETRACK_SATCAT_URL = (
    "https://www.space-track.org/basicspacedata/query"
    "/class/satcat/CURRENT/Y/orderby/NORAD_CAT_ID"
    "/format/json"
)


async def fetch_satcat_types() -> list[dict]:
    """Fetch OBJECT_TYPE for all current objects from Space-Track SATCAT."""
    if not settings.spacetrack_username or not settings.spacetrack_password:
        logger.warning("SATCAT fetch skipped: no Space-Track credentials")
        return []

    async with httpx.AsyncClient(timeout=180.0) as client:
        # Authenticate
        login_resp = await client.post(
            SPACETRACK_LOGIN_URL,
            data={
                "identity": settings.spacetrack_username,
                "password": settings.spacetrack_password,
            },
        )
        login_resp.raise_for_status()

        # Fetch SATCAT — only need NORAD_CAT_ID and OBJECT_TYPE
        # Use predicate to only get the fields we need
        url = (
            "https://www.space-track.org/basicspacedata/query"
            "/class/satcat/CURRENT/Y"
            "/predicates/NORAD_CAT_ID,OBJECT_TYPE,COUNTRY"
            "/format/json"
        )
        resp = await client.get(url)
        resp.raise_for_status()

        records = resp.json()
        logger.info(f"Fetched {len(records)} SATCAT records from Space-Track")
        return records


async def update_object_types(session: AsyncSession, satcat_records: list[dict]) -> int:
    """Update object_type in gp_elements from SATCAT data."""
    if not satcat_records:
        return 0

    count = 0
    # Process in batches
    for record in satcat_records:
        norad_id = record.get("NORAD_CAT_ID")
        obj_type = record.get("OBJECT_TYPE")
        country = record.get("COUNTRY")
        if not norad_id or not obj_type:
            continue

        result = await session.execute(
            text("""
                UPDATE gp_elements
                SET object_type = :obj_type,
                    country_code = COALESCE(:country, country_code)
                WHERE norad_cat_id = :norad_id
                  AND (object_type = 'UNKNOWN' OR object_type != :obj_type)
            """),
            {"norad_id": int(norad_id), "obj_type": obj_type, "country": country}
        )
        if result.rowcount > 0:
            count += 1

    await session.commit()
    logger.info(f"Updated object_type for {count} satellites")
    return count
