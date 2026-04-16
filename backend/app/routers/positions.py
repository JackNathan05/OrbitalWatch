"""Satellite position endpoints."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import SatellitePosition, OrbitTrail
from app.services.cache import get_cached_positions
from app.services.propagator import propagate_tle, propagate_omm, propagate_orbit_trail

router = APIRouter(tags=["positions"])


def _propagate_row(row, now: datetime) -> Optional[SatellitePosition]:
    """Propagate a single satellite row to current position."""
    pos = None

    # Try TLE lines first
    if row.tle_line1 and row.tle_line2:
        pos = propagate_tle(row.tle_line1, row.tle_line2, now)

    # Fall back to OMM Keplerian elements
    if pos is None and row.mean_motion and row.epoch:
        pos = propagate_omm(
            norad_id=row.norad_cat_id,
            epoch=row.epoch if row.epoch.tzinfo else row.epoch.replace(tzinfo=timezone.utc),
            mean_motion=row.mean_motion,
            eccentricity=row.eccentricity or 0.0,
            inclination=row.inclination or 0.0,
            ra_of_asc_node=row.ra_of_asc_node or 0.0,
            arg_of_pericenter=row.arg_of_pericenter or 0.0,
            mean_anomaly=row.mean_anomaly or 0.0,
            bstar=row.bstar or 0.0,
            dt=now,
        )

    if pos:
        lat, lon, alt = pos
        return SatellitePosition(
            norad_cat_id=row.norad_cat_id,
            object_name=row.object_name,
            object_type=row.object_type,
            latitude=round(lat, 4),
            longitude=round(lon, 4),
            altitude_km=round(alt, 2),
        )
    return None


@router.get("/positions", response_model=list[SatellitePosition])
async def get_positions(
    limit: int = Query(2000, ge=1, le=10000),
    object_type: Optional[str] = Query(None, description="PAYLOAD, ROCKET BODY, DEBRIS, UNKNOWN"),
    db: AsyncSession = Depends(get_db),
):
    """Returns lat/lon/alt for tracked satellites. Uses Redis cache when available,
    falls back to computing from OMM elements in the database."""
    # Try cache first
    cached = await get_cached_positions()
    if cached:
        results = cached
        if object_type:
            results = [p for p in results if p["object_type"] == object_type.upper()]
        return results[:limit]

    # Compute from database using OMM elements
    query = """
        SELECT norad_cat_id, object_name, object_type,
               tle_line1, tle_line2,
               epoch, mean_motion, eccentricity, inclination,
               ra_of_asc_node, arg_of_pericenter, mean_anomaly, bstar
        FROM gp_elements
        WHERE mean_motion IS NOT NULL AND mean_motion > 0
    """
    params: dict = {}
    if object_type:
        query += " AND object_type = :object_type"
        params["object_type"] = object_type.upper()
    query += " ORDER BY norad_cat_id LIMIT :limit"
    params["limit"] = limit

    result = await db.execute(text(query), params)
    rows = result.fetchall()

    now = datetime.now(timezone.utc)
    positions = []
    for row in rows:
        sat_pos = _propagate_row(row, now)
        if sat_pos:
            positions.append(sat_pos)

    return positions


@router.get("/positions/{norad_id}/trail", response_model=OrbitTrail)
async def get_orbit_trail(
    norad_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Returns 60 points along a satellite's orbit path, 30 min before and after now."""
    result = await db.execute(
        text("""
            SELECT tle_line1, tle_line2, norad_cat_id,
                   epoch, mean_motion, eccentricity, inclination,
                   ra_of_asc_node, arg_of_pericenter, mean_anomaly, bstar
            FROM gp_elements WHERE norad_cat_id = :id
        """),
        {"id": norad_id}
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Satellite not found")

    if row.tle_line1 and row.tle_line2:
        points = propagate_orbit_trail(tle_line1=row.tle_line1, tle_line2=row.tle_line2)
    elif row.mean_motion:
        epoch = row.epoch if row.epoch.tzinfo else row.epoch.replace(tzinfo=timezone.utc)
        points = propagate_orbit_trail(omm_params={
            "norad_id": row.norad_cat_id,
            "epoch": epoch,
            "mean_motion": row.mean_motion,
            "eccentricity": row.eccentricity or 0.0,
            "inclination": row.inclination or 0.0,
            "ra_of_asc_node": row.ra_of_asc_node or 0.0,
            "arg_of_pericenter": row.arg_of_pericenter or 0.0,
            "mean_anomaly": row.mean_anomaly or 0.0,
            "bstar": row.bstar or 0.0,
        })
    else:
        raise HTTPException(status_code=404, detail="No orbital data available")

    return OrbitTrail(norad_cat_id=norad_id, points=points)
