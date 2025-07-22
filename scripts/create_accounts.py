"""Create demo accounts in Postgres so you can test transfers immediately.

Usage (from repo root):
  docker compose run --rm gateway python scripts/create_accounts.py

This script is idempotent: it will not duplicate accounts.
"""

import os
import asyncio
import asyncpg

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "easpayments")
POSTGRES_USER = os.getenv("POSTGRES_USER", "easuser")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "easpass")

# hard-coded demo accounts
ACCOUNTS = [
    ("00000000-0000-0000-0000-0000000000a1", "Alice", 1_000_00),  # ₹1,000.00 in paise
    ("00000000-0000-0000-0000-0000000000b1", "Bob",   500_00),   # ₹500.00
    ("00000000-0000-0000-0000-0000000000c1", "Charlie", 0),
]

async def main():
    conn = await asyncpg.connect(
        host=POSTGRES_HOST, port=POSTGRES_PORT, user=POSTGRES_USER, password=POSTGRES_PASSWORD, database=POSTGRES_DB
    )

    # ensure tables exist (in case ledger hasn't started yet)
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            currency TEXT NOT NULL DEFAULT 'INR',
            start_balance BIGINT NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    for acct_id, name, start_balance in ACCOUNTS:
        await conn.execute(
            """
            INSERT INTO accounts (id, name, currency, start_balance)
            VALUES ($1, $2, 'INR', $3)
            ON CONFLICT (id) DO NOTHING
            """,
            acct_id, name, start_balance,
        )

    await conn.close()
    print("Accounts created / ensured.")

if __name__ == "__main__":
    asyncio.run(main())
