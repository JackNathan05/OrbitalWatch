"""Fetch and ingest TLE/GP data from CelesTrak into the database.

Usage: python ingest_tles.py [group]
  group: CelesTrak group name (default: 'active')
         Options: active, stations, visual, starlink, analyst, gpz, gpz-plus
"""
import asyncio
import sys

from app.database import async_session, init_db
from app.services.tle_ingest import fetch_gp_data, ingest_gp_data
from app.services.cache import set_last_update, LAST_TLE_UPDATE_KEY


async def main():
    group = sys.argv[1] if len(sys.argv) > 1 else "active"

    print(f"Initializing database...")
    await init_db()

    print(f"Fetching GP data from CelesTrak (group={group})...")
    records = await fetch_gp_data(group)
    print(f"Fetched {len(records)} satellite records")

    print("Ingesting into database...")
    async with async_session() as session:
        count = await ingest_gp_data(session, records)

    await set_last_update(LAST_TLE_UPDATE_KEY)
    print(f"Done! Ingested {count} satellites.")


if __name__ == "__main__":
    asyncio.run(main())
