from datetime import datetime

from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, DateTime, Text, Index,
    UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class GPElement(Base):
    __tablename__ = "gp_elements"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    norad_cat_id = Column(Integer, nullable=False, index=True)
    object_name = Column(String(100), nullable=False)
    object_type = Column(String(20), nullable=False)  # PAYLOAD, ROCKET BODY, DEBRIS, UNKNOWN
    object_id = Column(String(20))
    country_code = Column(String(10))
    launch_date = Column(DateTime)
    epoch = Column(DateTime(timezone=True), nullable=False)
    mean_motion = Column(Float, nullable=False)
    eccentricity = Column(Float, nullable=False)
    inclination = Column(Float, nullable=False)
    ra_of_asc_node = Column(Float)
    arg_of_pericenter = Column(Float)
    mean_anomaly = Column(Float)
    bstar = Column(Float)
    period_minutes = Column(Float)
    apogee_km = Column(Float)
    perigee_km = Column(Float)
    tle_line1 = Column(String(70))
    tle_line2 = Column(String(70))
    ingested_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("norad_cat_id", name="uq_gp_norad_cat_id"),
        Index("ix_gp_object_name", "object_name"),
        Index("ix_gp_object_type", "object_type"),
    )


class CDM(Base):
    __tablename__ = "cdm"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    cdm_id = Column(String(100), unique=True, nullable=False)
    tca = Column(DateTime(timezone=True), nullable=False, index=True)
    sat1_norad_id = Column(Integer, nullable=False, index=True)
    sat1_object_name = Column(String(100))
    sat1_object_type = Column(String(20))
    sat2_norad_id = Column(Integer, nullable=False, index=True)
    sat2_object_name = Column(String(100))
    sat2_object_type = Column(String(20))
    miss_distance_m = Column(Float, nullable=False)
    collision_probability = Column(Float, nullable=False, index=True)
    relative_speed_ms = Column(Float)
    creation_date = Column(DateTime(timezone=True), nullable=False)
    raw_json = Column(JSONB)
    ingested_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("ix_cdm_tca_pc", "tca", "collision_probability"),
    )
