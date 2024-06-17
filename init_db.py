import asyncio

from databases import Database

from config import database


async def init(database: Database) -> None:
    await database.connect()

    await database.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            coins REAL DEFAULT 1000
        );
    """)

    await database.execute("""
        CREATE TABLE IF NOT EXISTS bets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            event_date TEXT,
            driver_id INTEGER,
            bet_value REAL,
            payout_flag BOOLEAN DEFAULT TRUE
        );
    """)

    await database.disconnect()


asyncio.run(init(database))
