"""Fetch and ingest CDM data from Space-Track.org into the database.

Usage: python ingest_cdms.py [days_ahead] [min_pc]
  days_ahead: number of days to look ahead (default: 7)
  min_pc:     minimum collision probability (default: 1e-6)

Requires SPACETRACK_USERNAME and SPACETRACK_PASSWORD in .env
"""
import asyncio
import sys

from app.database import async_session, init_db
from app.services.cdm_ingest import fetch_cdm_data, ingest_cdm_data
from app.services.cache import set_last_update, LAST_CDM_UPDATE_KEY


async def main():
    days_ahead = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    min_pc = float(sys.argv[2]) if len(sys.argv) > 2 else 1e-6

    print("Initializing database...")
    await init_db()

    print(f"Fetching CDMs from Space-Track.org (next {days_ahead} days, Pc > {min_pc})...")
    cdms = await fetch_cdm_data(days_ahead=days_ahead, min_pc=min_pc)
    print(f"Fetched {len(cdms)} CDM records")

    print("Ingesting into database...")
    async with async_session() as session:
        count = await ingest_cdm_data(session, cdms)

    await set_last_update(LAST_CDM_UPDATE_KEY)
    print(f"Done! Ingested {count} conjunction records.")


if __name__ == "__main__":
    asyncio.run(main())
