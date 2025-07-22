"""Idempotency utilities bridging the gateway DB + request flow."""

from typing import Optional

from . import db

async def check_idempotency(key: str):
    rec = await db.get_idempotency_record(key)
    if not rec:
        return None
    return rec

async def start_idempotency(key: str):
    await db.create_idempotency_record(key)

async def finalize_idempotency(key: str, status: str, tx_id: Optional[str], response_obj):
    await db.finalize_idempotency_record(key, status, tx_id, response_obj)
