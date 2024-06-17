import asyncio

from config import db


async def init() -> None:
    await db.connect()

    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            coins REAL DEFAULT 1000
        );
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS bets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            event_date TEXT,
            driver_id INTEGER,
            bet_value REAL,
            payout_flag BOOLEAN DEFAULT TRUE
        );
    """)

    await db.disconnect()


asyncio.run(init())
