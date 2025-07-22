"""Core ledger operations."""

import uuid
from typing import Tuple
from sqlalchemy import select, insert, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from .db import accounts, ledger_entries

async def get_account_currency(session: AsyncSession, account_id: str) -> str | None:
    res = await session.execute(select(accounts.c.currency).where(accounts.c.id == account_id))
    return res.scalar_one_or_none()

async def get_balance(session: AsyncSession, account_id: str) -> int:
    # start_balance + credits - debits
    sb_res = await session.execute(select(accounts.c.start_balance).where(accounts.c.id == account_id))
    start_balance = sb_res.scalar_one_or_none() or 0
    sum_expr = func.sum(
        case((ledger_entries.c.direction == 'CREDIT', ledger_entries.c.amount), else_=-ledger_entries.c.amount)
    )
    le_res = await session.execute(
        select(func.coalesce(sum_expr, 0)).where(ledger_entries.c.account_id == account_id)
    )
    delta = le_res.scalar_one_or_none() or 0
    return int(start_balance + delta)

async def record_transfer(session: AsyncSession, from_acct: str, to_acct: str, amount: int, currency: str) -> Tuple[str, int, int]:
    tx_id = str(uuid.uuid4())
    # insert two rows
    await session.execute(insert(ledger_entries).values(tx_id=tx_id, account_id=from_acct, direction='DEBIT', amount=amount))
    await session.execute(insert(ledger_entries).values(tx_id=tx_id, account_id=to_acct, direction='CREDIT', amount=amount))
    # compute balances
    from_bal = await get_balance(session, from_acct)
    to_bal = await get_balance(session, to_acct)
    return tx_id, from_bal, to_bal

async def get_all_entries(session: AsyncSession):
    # join ledger_entries with accounts to get from_account and to_account
    debit_leg = ledger_entries.alias("debit_leg")
    credit_leg = ledger_entries.alias("credit_leg")
    query = (
        select(
            debit_leg.c.tx_id,
            debit_leg.c.account_id.label("from_account"),
            credit_leg.c.account_id.label("to_account"),
            debit_leg.c.amount,
            accounts.c.currency,
            debit_leg.c.created_at,
        )
        .join(credit_leg, debit_leg.c.tx_id == credit_leg.c.tx_id)
        .join(accounts, debit_leg.c.account_id == accounts.c.id)
        .where(debit_leg.c.direction == "DEBIT")
        .where(credit_leg.c.direction == "CREDIT")
    )
    res = await session.execute(query)
    return res.mappings().all()
