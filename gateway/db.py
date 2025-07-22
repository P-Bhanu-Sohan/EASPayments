"""Async DB utilities for the API gateway.

We maintain lightweight access to Postgres for:
  * idempotency key table
  * accounts table read (for validation)

The actual ledger writes are done by the ledger gRPC service; however we do a quick existence
check here so we can return 400 quickly instead of calling ledger for obviously bad input.
"""

import uuid
from typing import Optional

from sqlalchemy import (
    MetaData, Table, Column, String, BigInteger, DateTime, text, select, insert, JSON as SA_JSON
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker

from .config import settings

DATABASE_URL = (
    f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
    f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
)

metadata = MetaData()

accounts = Table(
    "accounts", metadata,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("currency", String, nullable=False, server_default=text("'INR'")),
    Column("start_balance", BigInteger, nullable=False, server_default=text("0")),
    Column("created_at", DateTime(timezone=True), server_default=text("now()")),
)

idempotency_keys = Table(
    "idempotency_keys", metadata,
    Column("key", String, primary_key=True),
    Column("tx_id", String, nullable=True),
    Column("status", String, nullable=False, server_default=text("'IN_PROGRESS'")),
    Column("response", SA_JSON, nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=text("now()")),
)

notifications = Table(
    "notifications", metadata,
    Column("id", String, primary_key=True, default=lambda: str(uuid.uuid4())),
    Column("account_id", String, nullable=False),
    Column("tx_id", String, nullable=False),
    Column("direction", String, nullable=False),
    Column("amount", BigInteger, nullable=False),
    Column("currency", String, nullable=False),
    Column("message", String, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=text("now()")),
)

_engine: Optional[AsyncEngine] = None
_async_session = None

async def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
    return _engine

async def get_session() -> AsyncSession:
    global _async_session
    if _async_session is None:
        engine = await get_engine()
        _async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return _async_session()

async def ensure_tables_exist():
    # This only creates tables if missing; ledger service also applies migrations.
    engine = await get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)

async def account_exists(account_id: str) -> bool:
    async with await get_session() as session:
        q = select(accounts.c.id).where(accounts.c.id == account_id)
        res = await session.execute(q)
        return res.scalar_one_or_none() is not None

async def get_account_currency(account_id: str) -> Optional[str]:
    async with await get_session() as session:
        q = select(accounts.c.currency).where(accounts.c.id == account_id)
        res = await session.execute(q)
        return res.scalar_one_or_none()

async def create_idempotency_record(key: str, tx_id: Optional[str] = None, status: str = "IN_PROGRESS"):
    from sqlalchemy.exc import IntegrityError

    async with await get_session() as session:
        try:
            stmt = insert(idempotency_keys).values(key=key, tx_id=tx_id, status=status)
            await session.execute(stmt)
            await session.commit()
        except IntegrityError:
            # Idempotency key already exists, which is fine
            await session.rollback()
        except Exception:
            await session.rollback()
            raise

async def get_idempotency_record(key: str):
    async with await get_session() as session:
        q = select(idempotency_keys).where(idempotency_keys.c.key == key)
        res = await session.execute(q)
        row = res.mappings().first()
        return dict(row) if row else None

async def finalize_idempotency_record(key: str, status: str, tx_id: Optional[str], response_obj):
    async with await get_session() as session:
        stmt = (
            idempotency_keys.update()
            .where(idempotency_keys.c.key == key)
            .values(status=status, tx_id=tx_id, response=response_obj)
        )
        await session.execute(stmt)
        await session.commit()
