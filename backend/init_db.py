"""Initialize the database tables. Run this before any ingestion scripts.

Usage: python init_db.py
"""
import asyncio
from app.database import init_db


async def main():
    print("Creating database tables...")
    await init_db()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
