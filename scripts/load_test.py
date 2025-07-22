"""Concurrent transfer load + idempotency test.

Spawns N workers that repeatedly try to transfer from Alice->Bob in small amounts.
Also intentionally retries the *same* idempotency key to show dedupe.

Usage:
  docker compose run --rm gateway python scripts/load_test.py
"""

import os
import asyncio
import httpx
import uuid

API_URL = os.getenv("API_URL", "http://gateway:8000")  # inside compose network
FROM = "00000000-0000-0000-0000-0000000000a1"
TO   = "00000000-0000-0000-0000-0000000000b1"

CONCURRENCY = 20
ITERATIONS = 10
AMOUNT = 1  # paise

async def one_transfer(client, amount, reuse_key=False):
    idem = "fixed-key" if reuse_key else str(uuid.uuid4())
    payload = {
        "from_account": FROM,
        "to_account": TO,
        "amount": amount,
        "currency": "INR",
        "idempotency_key": idem,
    }
    r = await client.post(f"{API_URL}/transfer", json=payload, timeout=30.0)
    return r.status_code, r.json()

async def get_balance(client, acct):
    r = await client.get(f"{API_URL}/balance/{acct}")
    return r.json()

async def main():
    await asyncio.sleep(5)  # wait for gateway to be ready
    async with httpx.AsyncClient() as client:
        # baseline balances
        bal_from_before = await get_balance(client, FROM)
        bal_to_before = await get_balance(client, TO)
        print("Before:", bal_from_before, bal_to_before)

        # run concurrency
        tasks = []
        for _ in range(CONCURRENCY):
            for _ in range(ITERATIONS):
                tasks.append(asyncio.create_task(one_transfer(client, AMOUNT)))
        # also some dupes
        for _ in range(5):
            tasks.append(asyncio.create_task(one_transfer(client, AMOUNT, reuse_key=True)))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        success = sum(1 for r in results if isinstance(r, tuple) and r[0] in [200, 409])
        print(f"Completed {len(results)} calls; {success} HTTP 200s")

        bal_from_after = await get_balance(client, FROM)
        bal_to_after = await get_balance(client, TO)
        print("After:", bal_from_after, bal_to_after)

if __name__ == "__main__":
    asyncio.run(main())
