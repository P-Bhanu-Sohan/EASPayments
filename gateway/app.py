"""FastAPI Gateway for EASPayments.

Public REST surface:

POST /transfer        -> initiate transfer (idempotent)
GET  /balance/{acct}  -> fetch balance
GET  /health          -> liveness
"""

import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from loguru import logger

from .config import settings
from .schemas import TransferIn, TransferOut, BalanceOut
from . import db, idempotency, redis_lock, grpc_clients, utils

app = FastAPI(title="EASPayments Gateway")

app.mount("/ui", StaticFiles(directory="UI", html=True), name="ui")

@app.on_event("startup")
async def _startup():
    await db.ensure_tables_exist()

@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/accounts")
async def get_accounts():
    session = await db.get_session()
    async with session:
        query = db.accounts.select()
        result = await session.execute(query)
        return [dict(r) for r in result.mappings().all()]

@app.get("/ledger_entries")
async def get_ledger_entries():
    resp = await grpc_clients.ledger_get_all_entries()
    return [
        dict(
            tx_id=e.tx_id,
            from_account=e.from_account,
            to_account=e.to_account,
            amount=e.amount,
            currency=e.currency,
            created_at=e.created_at,
        )
        for e in resp.entries
    ]

@app.get("/idempotency_keys")
async def get_idempotency_keys():
    session = await db.get_session()
    async with session:
        query = db.idempotency_keys.select()
        result = await session.execute(query)
        return [dict(r) for r in result.mappings().all()]

@app.get("/balance/{account_id}", response_model=BalanceOut)
async def get_balance(account_id: str):
    if not utils.is_uuid(account_id):
        raise HTTPException(status_code=400, detail="Invalid account_id")
    resp = await grpc_clients.ledger_get_balance(account_id)
    return BalanceOut(account_id=resp.account_id, balance=resp.balance, currency=resp.currency)

@app.post("/transfer", response_model=TransferOut)
async def transfer(req: TransferIn):
    # idempotency pre-check
    existing = await idempotency.check_idempotency(req.idempotency_key)
    if existing and existing["status"] == "SUCCESS" and existing["response"]:
        return existing["response"]

    # create placeholder idempotency record (no-op if exists)
    await idempotency.start_idempotency(req.idempotency_key)

    # validate accounts
    if not await db.account_exists(req.from_account):
        raise HTTPException(status_code=400, detail="from_account not found")
    if not await db.account_exists(req.to_account):
        raise HTTPException(status_code=400, detail="to_account not found")

    # concurrency control: acquire account locks
    locks = {}
    try:
        locks = await redis_lock.acquire_account_locks([req.from_account, req.to_account])
    except TimeoutError as e:
        raise HTTPException(status_code=409, detail=str(e))

    # call ledger
    try:
        grpc_resp = await grpc_clients.ledger_transfer(
            from_account=req.from_account,
            to_account=req.to_account,
            amount=req.amount,
            currency=req.currency,
            idempotency_key=req.idempotency_key,
        )
    finally:
        await redis_lock.release_account_locks(locks)

    # build response model
    resp_obj = TransferOut(
        tx_id=grpc_resp.tx_id,
        from_account=grpc_resp.from_account,
        to_account=grpc_resp.to_account,
        amount=grpc_resp.amount,
        currency=grpc_resp.currency,
        from_balance_after=grpc_resp.from_balance_after,
        to_balance_after=grpc_resp.to_balance_after,
        status=grpc_resp.status,
        message=grpc_resp.message or None,
    ).model_dump()

    # persist idempotency final state
    await idempotency.finalize_idempotency(
        req.idempotency_key, grpc_resp.status, grpc_resp.tx_id, resp_obj
    )

    # fire notifications (don't block response)
    asyncio.create_task(_notify_both(grpc_resp))

    return resp_obj

async def _notify_both(grpc_resp):
    try:
        # Store notifications in the database
        session = await db.get_session()
        async with session:
            async with session.begin():
                await session.execute(
                    db.notifications.insert().values(
                        account_id=grpc_resp.from_account,
                        tx_id=grpc_resp.tx_id,
                        amount=grpc_resp.amount,
                        direction="DEBIT",
                        currency=grpc_resp.currency,
                        message=f"Sent {grpc_resp.amount} {grpc_resp.currency} to {grpc_resp.to_account}",
                    )
                )
                await session.execute(
                    db.notifications.insert().values(
                        account_id=grpc_resp.to_account,
                        tx_id=grpc_resp.tx_id,
                        amount=grpc_resp.amount,
                        direction="CREDIT",
                        currency=grpc_resp.currency,
                        message=f"Received {grpc_resp.amount} {grpc_resp.currency} from {grpc_resp.from_account}",
                    )
                )

        # Asynchronously send notifications
        try:
            await grpc_clients.send_notification(
                account_id=grpc_resp.from_account,
                tx_id=grpc_resp.tx_id,
                amount=grpc_resp.amount,
                direction="DEBIT",
                currency=grpc_resp.currency,
                message=f"Sent {grpc_resp.amount} {grpc_resp.currency} to {grpc_resp.to_account}",
            )
            logger.info(f"Notification sent for debit: {grpc_resp.from_account}")
        except Exception as e:
            logger.error(f"Error sending debit notification for {grpc_resp.from_account}: {e}")

        try:
            await grpc_clients.send_notification(
                account_id=grpc_resp.to_account,
                tx_id=grpc_resp.tx_id,
                amount=grpc_resp.amount,
                direction="CREDIT",
                currency=grpc_resp.currency,
                message=f"Received {grpc_resp.amount} {grpc_resp.currency} from {grpc_resp.from_account}",
            )
            logger.info(f"Notification sent for credit: {grpc_resp.to_account}")
        except Exception as e:
            logger.error(f"Error sending credit notification for {grpc_resp.to_account}: {e}")

    except Exception as e:
        # swallow notification failures; they don't affect ledger
        logger.error(f"Unhandled exception in _notify_both: {e}")
        pass

@app.get("/notifications")
async def get_notifications():
    session = await db.get_session()
    async with session:
        query = db.notifications.select()
        result = await session.execute(query)
        return [dict(r) for r in result.mappings().all()]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("gateway.app:app", host=settings.api_host, port=settings.api_port, reload=False)
