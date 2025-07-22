"""Simple Redis distributed lock helper.

We acquire locks for *both* accounts involved in a transfer to avoid race conditions.
Locks auto-expire (safety valve) but we also explicitly release.

We sort account IDs to provide a deterministic lock acquisition ordering across callers,
which reduces deadlock risk.
"""

import uuid
from typing import Iterable, Dict

import redis.asyncio as redis

from .config import settings

_redis_client = None

async def get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client

LOCK_PREFIX = "acctlock:"
DEFAULT_TTL_MS = 10_000  # 10s

async def acquire_account_locks(account_ids: Iterable[str], ttl_ms: int = DEFAULT_TTL_MS) -> Dict[str, str]:
    """Acquire locks for all account_ids; return dict {acct_id: lock_token}. Raises TimeoutError."""
    r = await get_redis()
    tokens = {}
    # sort to avoid deadlock
    for acct in sorted(account_ids):
        token = str(uuid.uuid4())
        ok = await r.set(LOCK_PREFIX + acct, token, nx=True, px=ttl_ms)
        if not ok:
            # rollback previously acquired
            await release_account_locks(tokens)
            raise TimeoutError(f"Failed to acquire lock for account {acct}")
        tokens[acct] = token
    return tokens

async def release_account_locks(tokens: Dict[str, str]):
    r = await get_redis()
    # lua script to release only if token matches
    lua = """
    if redis.call('get', KEYS[1]) == ARGV[1] then
      return redis.call('del', KEYS[1])
    else
      return 0
    end
    """
    for acct, token in tokens.items():
        key = LOCK_PREFIX + acct
        await r.eval(lua, 1, key, token)
