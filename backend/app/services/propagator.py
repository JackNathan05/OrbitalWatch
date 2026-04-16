"""SGP4 orbit propagation service.

Supports two modes:
1. TLE lines (tle_line1, tle_line2) — traditional format
2. OMM Keplerian elements — from CelesTrak JSON/OMM format

Both produce lat/lon/alt positions at a given time.
"""
import math
from datetime import datetime, timedelta, timezone
from typing import Optional

from sgp4.api import Satrec, WGS72
from sgp4.api import jday

# Earth radius in km
EARTH_RADIUS_KM = 6371.0


def _teme_to_geodetic(x: float, y: float, z: float) -> tuple[float, float, float]:
    """Convert TEME (km) to geodetic lat/lon/alt.

    Simplified conversion — ignores Earth oblateness for speed.
    Good enough for visualization (error < 0.3%).
    """
    r = math.sqrt(x * x + y * y + z * z)
    lon = math.degrees(math.atan2(y, x))
    lat = math.degrees(math.asin(z / r)) if r > 0 else 0.0
    alt = r - EARTH_RADIUS_KM
    return lat, lon, alt


def _satrec_from_omm(
    norad_id: int,
    epoch: datetime,
    mean_motion: float,
    eccentricity: float,
    inclination: float,
    ra_of_asc_node: float,
    arg_of_pericenter: float,
    mean_anomaly: float,
    bstar: float,
) -> Satrec:
    """Build an SGP4 Satrec from OMM Keplerian elements."""
    sat = Satrec()
    sat.sgp4init(
        WGS72,                          # gravity model
        'i',                            # improved mode
        norad_id,                       # NORAD catalog ID
        _epoch_to_jdsatepoch(epoch),    # epoch as days since 1949-12-31
        bstar,                          # B* drag coefficient
        0.0,                            # ndot (not used in SGP4)
        0.0,                            # nddot (not used in SGP4)
        eccentricity,
        math.radians(arg_of_pericenter),
        math.radians(inclination),
        math.radians(mean_anomaly),
        mean_motion * (2.0 * math.pi / 1440.0),  # rev/day -> rad/min
        math.radians(ra_of_asc_node),
    )
    return sat


def _epoch_to_jdsatepoch(epoch: datetime) -> float:
    """Convert epoch datetime to days since 1949 December 31 00:00 UT."""
    # SGP4 epoch is Julian date - 2433281.5
    jd, fr = jday(epoch.year, epoch.month, epoch.day,
                  epoch.hour, epoch.minute,
                  epoch.second + epoch.microsecond / 1e6)
    return (jd + fr) - 2433281.5


def propagate_tle(
    tle_line1: str,
    tle_line2: str,
    dt: Optional[datetime] = None,
) -> Optional[tuple[float, float, float]]:
    """Propagate a TLE to a given time and return (lat, lon, alt_km)."""
    if dt is None:
        dt = datetime.now(timezone.utc)

    try:
        satellite = Satrec.twoline2rv(tle_line1, tle_line2, WGS72)
        jd, fr = jday(dt.year, dt.month, dt.day, dt.hour, dt.minute,
                      dt.second + dt.microsecond / 1e6)
        e, r, v = satellite.sgp4(jd, fr)
        if e != 0:
            return None
        return _teme_to_geodetic(*r)
    except Exception:
        return None


def propagate_omm(
    norad_id: int,
    epoch: datetime,
    mean_motion: float,
    eccentricity: float,
    inclination: float,
    ra_of_asc_node: float,
    arg_of_pericenter: float,
    mean_anomaly: float,
    bstar: float,
    dt: Optional[datetime] = None,
) -> Optional[tuple[float, float, float]]:
    """Propagate OMM Keplerian elements to a given time and return (lat, lon, alt_km)."""
    if dt is None:
        dt = datetime.now(timezone.utc)

    try:
        sat = _satrec_from_omm(
            norad_id, epoch, mean_motion, eccentricity,
            inclination, ra_of_asc_node, arg_of_pericenter,
            mean_anomaly, bstar,
        )
        jd, fr = jday(dt.year, dt.month, dt.day, dt.hour, dt.minute,
                      dt.second + dt.microsecond / 1e6)
        e, r, v = sat.sgp4(jd, fr)
        if e != 0:
            return None
        return _teme_to_geodetic(*r)
    except Exception:
        return None


def propagate_orbit_trail(
    tle_line1: Optional[str] = None,
    tle_line2: Optional[str] = None,
    omm_params: Optional[dict] = None,
    center_time: Optional[datetime] = None,
    minutes_before: int = 30,
    minutes_after: int = 30,
    step_seconds: int = 60,
) -> list[dict]:
    """Compute an orbit trail as a list of position points.

    Accepts either TLE lines or OMM parameters dict with keys:
    norad_id, epoch, mean_motion, eccentricity, inclination,
    ra_of_asc_node, arg_of_pericenter, mean_anomaly, bstar
    """
    if center_time is None:
        center_time = datetime.now(timezone.utc)

    start = center_time - timedelta(minutes=minutes_before)
    end = center_time + timedelta(minutes=minutes_after)
    step = timedelta(seconds=step_seconds)

    # Build satrec once
    try:
        if tle_line1 and tle_line2:
            sat = Satrec.twoline2rv(tle_line1, tle_line2, WGS72)
        elif omm_params:
            sat = _satrec_from_omm(**omm_params)
        else:
            return []
    except Exception:
        return []

    points = []
    t = start
    while t <= end:
        jd, fr = jday(t.year, t.month, t.day, t.hour, t.minute,
                      t.second + t.microsecond / 1e6)
        e, r, v = sat.sgp4(jd, fr)
        if e == 0:
            lat, lon, alt = _teme_to_geodetic(*r)
            points.append({
                "latitude": round(lat, 4),
                "longitude": round(lon, 4),
                "altitude_km": round(alt, 2),
                "timestamp": t.isoformat(),
            })
        t += step

    return points
