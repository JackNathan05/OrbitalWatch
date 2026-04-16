"""Fetch OBJECT_TYPE from Space-Track SATCAT and update the database.

Usage: python ingest_satcat.py
"""
import asyncio

from app.database import async_session, init_db
from app.services.satcat_ingest import fetch_satcat_types, update_object_types


async def main():
    print("Initializing database...")
    await init_db()

    print("Fetching SATCAT from Space-Track.org...")
    records = await fetch_satcat_types()
    print(f"Fetched {len(records)} SATCAT records")

    print("Updating object types...")
    async with async_session() as session:
        count = await update_object_types(session, records)

    print(f"Done! Updated {count} satellite object types.")


if __name__ == "__main__":
    asyncio.run(main())
