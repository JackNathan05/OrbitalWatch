from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# --- Satellite / Position Schemas ---

class SatellitePosition(BaseModel):
    norad_cat_id: int
    object_name: str
    object_type: str
    latitude: float
    longitude: float
    altitude_km: float


class SatelliteDetail(BaseModel):
    norad_cat_id: int
    object_name: str
    object_type: str
    object_id: Optional[str] = None
    country_code: Optional[str] = None
    launch_date: Optional[datetime] = None
    epoch: datetime
    mean_motion: float
    eccentricity: float
    inclination: float
    period_minutes: Optional[float] = None
    apogee_km: Optional[float] = None
    perigee_km: Optional[float] = None
    active_conjunction_count: int = 0


class SatelliteSearchResult(BaseModel):
    norad_cat_id: int
    object_name: str
    object_type: str
    apogee_km: Optional[float] = None
    perigee_km: Optional[float] = None
    conjunction_count: int = 0


# --- Conjunction / CDM Schemas ---

class ConjunctionSummary(BaseModel):
    cdm_id: str
    tca: datetime
    sat1_norad_id: int
    sat1_object_name: Optional[str] = None
    sat1_object_type: Optional[str] = None
    sat2_norad_id: int
    sat2_object_name: Optional[str] = None
    sat2_object_type: Optional[str] = None
    miss_distance_m: float
    collision_probability: float
    relative_speed_ms: Optional[float] = None
    risk_level: str  # GREEN, YELLOW, ORANGE, RED


class ConjunctionDetail(ConjunctionSummary):
    creation_date: datetime
    plain_english_summary: str
    raw_json: Optional[dict] = None


# --- Stats Schemas ---

class PlatformStats(BaseModel):
    total_objects_tracked: int
    active_conjunctions_7d: int
    high_risk_events: int  # Pc > 1e-3
    most_recent_high_risk: Optional[ConjunctionSummary] = None
    last_tle_update: Optional[datetime] = None
    last_cdm_update: Optional[datetime] = None


# --- Orbit Trail ---

class OrbitPoint(BaseModel):
    latitude: float
    longitude: float
    altitude_km: float
    timestamp: datetime


class OrbitTrail(BaseModel):
    norad_cat_id: int
    points: list[OrbitPoint]
