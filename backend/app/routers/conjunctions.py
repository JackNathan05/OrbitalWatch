"""Conjunction / CDM endpoints."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import ConjunctionSummary, ConjunctionDetail

router = APIRouter(tags=["conjunctions"])


def _risk_level(pc: float) -> str:
    if pc > 1e-3:
        return "RED"
    elif pc > 1e-4:
        return "ORANGE"
    elif pc > 1e-5:
        return "YELLOW"
    return "GREEN"


def _plain_english_summary(miss_distance_m: float, pc: float, relative_speed_ms: float | None) -> str:
    """Build a readable risk summary from CDM numbers."""
    if miss_distance_m < 100:
        dist_desc = f"{miss_distance_m:.0f} meters"
    elif miss_distance_m < 1000:
        dist_desc = f"{miss_distance_m:.0f} meters (about {miss_distance_m/100:.0f} football fields)"
    elif miss_distance_m < 10000:
        dist_desc = f"{miss_distance_m/1000:.1f} km"
    else:
        dist_desc = f"{miss_distance_m/1000:.1f} km"

    if pc > 1e-3:
        risk_desc = "HIGH RISK"
    elif pc > 1e-4:
        risk_desc = "ELEVATED RISK"
    elif pc > 1e-5:
        risk_desc = "LOW RISK"
    else:
        risk_desc = "MINIMAL RISK"

    speed_desc = ""
    if relative_speed_ms:
        speed_kmh = relative_speed_ms * 3.6
        speed_desc = f" Closing speed: {speed_kmh:,.0f} km/h ({relative_speed_ms:,.0f} m/s)."

    pc_readable = f"1 in {int(1/pc):,}" if pc > 0 else "negligible"

    return (
        f"{risk_desc}. Predicted miss distance: {dist_desc}. "
        f"Collision probability: ~{pc_readable} ({pc:.2e}).{speed_desc} "
        f"Most conjunctions don't lead to maneuvers. Operators use additional "
        f"non-public data when making avoidance decisions."
    )


@router.get("/conjunctions", response_model=list[ConjunctionSummary])
async def list_conjunctions(
    min_pc: float = Query(1e-5, description="Minimum collision probability"),
    days: int = Query(7, ge=1, le=30),
    risk_level_filter: Optional[str] = Query(None, description="GREEN, YELLOW, ORANGE, RED"),
    object_type: Optional[str] = Query(None, description="Filter by object type"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """CDMs for the next N days, sorted by Pc descending. Filterable by risk level and object type."""
    now = datetime.now(timezone.utc)
    tca_end = now + timedelta(days=days)

    query = """
        SELECT cdm_id, tca, sat1_norad_id, sat1_object_name, sat1_object_type,
               sat2_norad_id, sat2_object_name, sat2_object_type,
               miss_distance_m, collision_probability, relative_speed_ms
        FROM cdm
        WHERE collision_probability >= :min_pc
          AND tca >= :now AND tca <= :tca_end
    """
    params = {"min_pc": min_pc, "now": now, "tca_end": tca_end}

    if object_type:
        query += " AND (sat1_object_type = :obj_type OR sat2_object_type = :obj_type)"
        params["obj_type"] = object_type.upper()

    query += " ORDER BY collision_probability DESC LIMIT :limit"
    params["limit"] = limit

    result = await db.execute(text(query), params)
    rows = result.fetchall()

    conjunctions = []
    for row in rows:
        rl = _risk_level(row.collision_probability)
        if risk_level_filter and rl != risk_level_filter.upper():
            continue
        conjunctions.append(ConjunctionSummary(
            cdm_id=row.cdm_id,
            tca=row.tca,
            sat1_norad_id=row.sat1_norad_id,
            sat1_object_name=row.sat1_object_name,
            sat1_object_type=row.sat1_object_type,
            sat2_norad_id=row.sat2_norad_id,
            sat2_object_name=row.sat2_object_name,
            sat2_object_type=row.sat2_object_type,
            miss_distance_m=row.miss_distance_m,
            collision_probability=row.collision_probability,
            relative_speed_ms=row.relative_speed_ms,
            risk_level=rl,
        ))

    return conjunctions


@router.get("/conjunctions/{cdm_id}", response_model=ConjunctionDetail)
async def get_conjunction_detail(cdm_id: str, db: AsyncSession = Depends(get_db)):
    """Full CDM record for one conjunction, including a readable risk summary."""
    result = await db.execute(
        text("""
            SELECT cdm_id, tca, sat1_norad_id, sat1_object_name, sat1_object_type,
                   sat2_norad_id, sat2_object_name, sat2_object_type,
                   miss_distance_m, collision_probability, relative_speed_ms,
                   creation_date, raw_json
            FROM cdm WHERE cdm_id = :cdm_id
        """),
        {"cdm_id": cdm_id}
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="CDM not found")

    import json
    raw = json.loads(row.raw_json) if isinstance(row.raw_json, str) else row.raw_json

    return ConjunctionDetail(
        cdm_id=row.cdm_id,
        tca=row.tca,
        sat1_norad_id=row.sat1_norad_id,
        sat1_object_name=row.sat1_object_name,
        sat1_object_type=row.sat1_object_type,
        sat2_norad_id=row.sat2_norad_id,
        sat2_object_name=row.sat2_object_name,
        sat2_object_type=row.sat2_object_type,
        miss_distance_m=row.miss_distance_m,
        collision_probability=row.collision_probability,
        relative_speed_ms=row.relative_speed_ms,
        risk_level=_risk_level(row.collision_probability),
        creation_date=row.creation_date,
        plain_english_summary=_plain_english_summary(
            row.miss_distance_m, row.collision_probability, row.relative_speed_ms
        ),
        raw_json=raw,
    )
