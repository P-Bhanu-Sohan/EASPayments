"""Async DB engine & schema metadata for the ledger service."""

import os
from typing import Optional
from sqlalchemy import MetaData, Table, Column, String, BigInteger, DateTime, text, JSON as SA_JSON
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "easpayments")
POSTGRES_USER = os.getenv("POSTGRES_USER", "easuser")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "easpass")

DATABASE_URL = (
    f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
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

ledger_entries = Table(
    "ledger_entries", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("tx_id", String, nullable=False),
    Column("account_id", String, nullable=False),
    Column("direction", String, nullable=False),
    Column("amount", BigInteger, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=text("now()")),
)

idempotency_keys = Table(
    "idempotency_keys", metadata,
    Column("key", String, primary_key=True),
    Column("tx_id", String),
    Column("status", String, nullable=False, server_default=text("'IN_PROGRESS'")),
    Column("response", SA_JSON),
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

async def apply_migrations():
    # run raw SQL file
    engine = await get_engine()
    sql_path = os.path.join(os.path.dirname(__file__), "migrations.sql")
    with open(sql_path, "r", encoding="utf-8") as f:
        sql_text = f.read()
    async with engine.begin() as conn:
        for statement in sql_text.split(';')[:-1]: # Split by semicolon and ignore the last empty string
            await conn.execute(text(statement))
