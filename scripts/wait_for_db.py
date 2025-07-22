"""Simple wait-for-Postgres readiness."""
import asyncio
import asyncpg
import os

async def main():
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    user = os.getenv("POSTGRES_USER", "easuser")
    password = os.getenv("POSTGRES_PASSWORD", "easpass")
    db = os.getenv("POSTGRES_DB", "easpayments")

    while True:
        try:
            conn = await asyncpg.connect(host=host, port=port, user=user, password=password, database=db)
        except Exception:
            await asyncio.sleep(1)
        else:
            await conn.close()
            break

if __name__ == "__main__":
    asyncio.run(main())
