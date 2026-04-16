"""Run full initial data ingestion: TLEs from CelesTrak + CDMs from Space-Track.

Usage: python ingest_all.py
"""
import asyncio

from app.database import async_session, init_db
from app.services.tle_ingest import fetch_gp_data, ingest_gp_data
from app.services.cdm_ingest import fetch_cdm_data, ingest_cdm_data
from app.services.cache import set_last_update, LAST_TLE_UPDATE_KEY, LAST_CDM_UPDATE_KEY

TLE_GROUPS = [
    "stations", "visual", "starlink", "oneweb", "planet", "spire",
    "geo", "resource", "science", "military", "cubesat", "weather",
    "noaa", "gps-ops", "galileo", "beidou", "iridium-NEXT",
    "globalstar", "amateur", "last-30-days",
]


async def main():
    print("=" * 50)
    print("OrbitalWatch - Initial Data Ingestion")
    print("=" * 50)

    print("\nInitializing database...")
    await init_db()

    # --- TLE Ingestion ---
    total_tles = 0
    for group in TLE_GROUPS:
        print(f"\n[TLE] Fetching group '{group}' from CelesTrak...")
        try:
            records = await fetch_gp_data(group)
            print(f"[TLE] Fetched {len(records)} records")
            async with async_session() as session:
                count = await ingest_gp_data(session, records)
                total_tles += count
                print(f"[TLE] Ingested {count} records from '{group}'")
        except Exception as e:
            print(f"[TLE] Error with group '{group}': {e}")

    await set_last_update(LAST_TLE_UPDATE_KEY)
    print(f"\n[TLE] Total: {total_tles} satellites ingested")

    # --- CDM Ingestion ---
    print(f"\n[CDM] Fetching CDMs from Space-Track.org (next 7 days, Pc > 1e-6)...")
    try:
        cdms = await fetch_cdm_data(days_ahead=7, min_pc=1e-6)
        print(f"[CDM] Fetched {len(cdms)} records")
        async with async_session() as session:
            count = await ingest_cdm_data(session, cdms)
            print(f"[CDM] Ingested {count} conjunction records")
        await set_last_update(LAST_CDM_UPDATE_KEY)
    except Exception as e:
        print(f"[CDM] Error: {e}")
        print("[CDM] Make sure SPACETRACK_USERNAME and SPACETRACK_PASSWORD are set in .env")

    # --- Summary ---
    print("\n" + "=" * 50)
    print("Ingestion complete!")
    print(f"  Satellites: {total_tles}")
    print(f"  CDMs:       {count if 'count' in dir() else 'failed'}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
