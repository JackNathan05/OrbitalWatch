"""Satellite detail and search endpoints."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import SatelliteDetail, SatelliteSearchResult

router = APIRouter(tags=["satellites"])


@router.get("/satellites/search", response_model=list[SatelliteSearchResult])
async def search_satellites(
    q: str = Query(..., min_length=1, description="Search by name or NORAD ID"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Partial name match or exact NORAD ID lookup. Returns top results with conjunction counts."""
    # Check if query is a numeric NORAD ID
    try:
        norad_id = int(q)
        result = await db.execute(
            text("""
                SELECT g.norad_cat_id, g.object_name, g.object_type, g.apogee_km, g.perigee_km,
                       COUNT(c.id) as conjunction_count
                FROM gp_elements g
                LEFT JOIN cdm c ON (g.norad_cat_id = c.sat1_norad_id OR g.norad_cat_id = c.sat2_norad_id)
                    AND c.tca >= NOW() - INTERVAL '90 days'
                WHERE g.norad_cat_id = :norad_id
                GROUP BY g.norad_cat_id, g.object_name, g.object_type, g.apogee_km, g.perigee_km
            """),
            {"norad_id": norad_id}
        )
    except ValueError:
        # Search by name (case-insensitive partial match)
        result = await db.execute(
            text("""
                SELECT g.norad_cat_id, g.object_name, g.object_type, g.apogee_km, g.perigee_km,
                       COUNT(c.id) as conjunction_count
                FROM gp_elements g
                LEFT JOIN cdm c ON (g.norad_cat_id = c.sat1_norad_id OR g.norad_cat_id = c.sat2_norad_id)
                    AND c.tca >= NOW() - INTERVAL '90 days'
                WHERE UPPER(g.object_name) LIKE UPPER(:query)
                GROUP BY g.norad_cat_id, g.object_name, g.object_type, g.apogee_km, g.perigee_km
                ORDER BY conjunction_count DESC
                LIMIT :limit
            """),
            {"query": f"%{q}%", "limit": limit}
        )

    rows = result.fetchall()
    return [
        SatelliteSearchResult(
            norad_cat_id=row.norad_cat_id,
            object_name=row.object_name,
            object_type=row.object_type,
            apogee_km=row.apogee_km,
            perigee_km=row.perigee_km,
            conjunction_count=row.conjunction_count or 0,
        )
        for row in rows
    ]


@router.get("/satellites/{norad_id}", response_model=SatelliteDetail)
async def get_satellite(norad_id: int, db: AsyncSession = Depends(get_db)):
    """Orbital elements, metadata, and active conjunction count for one satellite."""
    result = await db.execute(
        text("SELECT * FROM gp_elements WHERE norad_cat_id = :id"),
        {"id": norad_id}
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Satellite not found")

    # Count active conjunctions
    conj_result = await db.execute(
        text("""
            SELECT COUNT(*) as cnt FROM cdm
            WHERE (sat1_norad_id = :id OR sat2_norad_id = :id)
              AND tca >= NOW() AND tca <= NOW() + INTERVAL '7 days'
              AND collision_probability >= 1e-5
        """),
        {"id": norad_id}
    )
    conj_count = conj_result.scalar() or 0

    return SatelliteDetail(
        norad_cat_id=row.norad_cat_id,
        object_name=row.object_name,
        object_type=row.object_type,
        object_id=row.object_id,
        country_code=row.country_code,
        launch_date=row.launch_date,
        epoch=row.epoch,
        mean_motion=row.mean_motion,
        eccentricity=row.eccentricity,
        inclination=row.inclination,
        period_minutes=row.period_minutes,
        apogee_km=row.apogee_km,
        perigee_km=row.perigee_km,
        active_conjunction_count=conj_count,
    )


@router.get("/satellites/{norad_id}/conjunctions", response_model=list)
async def get_satellite_conjunctions(
    norad_id: int,
    days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """CDMs involving this satellite over the past N days."""
    result = await db.execute(
        text("""
            SELECT cdm_id, tca, sat1_norad_id, sat1_object_name, sat1_object_type,
                   sat2_norad_id, sat2_object_name, sat2_object_type,
                   miss_distance_m, collision_probability, relative_speed_ms
            FROM cdm
            WHERE (sat1_norad_id = :id OR sat2_norad_id = :id)
              AND tca >= NOW() - make_interval(days => :days)
            ORDER BY tca DESC
            LIMIT 100
        """),
        {"id": norad_id, "days": days}
    )
    rows = result.fetchall()

    from app.routers.conjunctions import _risk_level
    return [
        {
            "cdm_id": row.cdm_id,
            "tca": row.tca.isoformat(),
            "sat1_norad_id": row.sat1_norad_id,
            "sat1_object_name": row.sat1_object_name,
            "sat2_norad_id": row.sat2_norad_id,
            "sat2_object_name": row.sat2_object_name,
            "miss_distance_m": row.miss_distance_m,
            "collision_probability": row.collision_probability,
            "risk_level": _risk_level(row.collision_probability),
        }
        for row in rows
    ]
