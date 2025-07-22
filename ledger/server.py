"""gRPC Ledger Service."""

import asyncio
import os
import grpc
from loguru import logger

from . import db, crud
from .db import get_session

import payment_pb2
import payment_pb2_grpc

LEDGER_GRPC_PORT = int(os.getenv("LEDGER_GRPC_PORT", "50051"))

class LedgerService(payment_pb2_grpc.LedgerServiceServicer):
    async def Transfer(self, request, context):  # type: ignore[override]
        from_acct = request.from_account
        to_acct = request.to_account
        amount = request.amount
        currency = request.currency or "INR"

        # Validate non-negative
        if amount <= 0:
            return payment_pb2.TransferResponse(
                tx_id="", from_account=from_acct, to_account=to_acct, amount=amount,
                currency=currency, from_balance_after=0, to_balance_after=0,
                status="FAILED", message="Amount must be > 0",
            )

        session = await get_session()
        try:
            async with session.begin():
                # ensure accounts exist
                from_curr = await crud.get_account_currency(session, from_acct)
                to_curr = await crud.get_account_currency(session, to_acct)
                if from_curr is None or to_curr is None:
                    raise ValueError("Account not found")
                if from_curr != to_curr:
                    raise ValueError("Currency mismatch")

                # check balance sufficiency
                from_bal_before = await crud.get_balance(session, from_acct)
                if from_bal_before < amount:
                    raise ValueError("Insufficient funds")

                tx_id, from_bal_after, to_bal_after = await crud.record_transfer(
                    session, from_acct, to_acct, amount, from_curr
                )
        except Exception as e:  # rollback auto on error
            logger.exception("Transfer error")
            return payment_pb2.TransferResponse(
                tx_id="", from_account=from_acct, to_account=to_acct, amount=amount,
                currency=currency, from_balance_after=0, to_balance_after=0,
                status="FAILED", message=str(e),
            )
        else:
            return payment_pb2.TransferResponse(
                tx_id=tx_id, from_account=from_acct, to_account=to_acct, amount=amount,
                currency=currency, from_balance_after=from_bal_after, to_balance_after=to_bal_after,
                status="SUCCESS", message="",
            )

    async def GetBalance(self, request, context):  # type: ignore[override]
        acct = request.account_id
        session = await get_session()
        async with session.begin():
            curr = await crud.get_account_currency(session, acct) or "INR"
            bal = await crud.get_balance(session, acct)
        return payment_pb2.BalanceResponse(account_id=acct, balance=bal, currency=curr)

    async def GetAllEntries(self, request, context):
        session = await get_session()
        async with session.begin():
            entries = await crud.get_all_entries(session)
        return payment_pb2.GetAllResponse(
            entries=[
                payment_pb2.LedgerEntry(
                    tx_id=e.tx_id,
                    from_account=e.from_account,
                    to_account=e.to_account,
                    amount=e.amount,
                    currency=e.currency,
                    created_at=str(e.created_at),
                )
                for e in entries
            ]
        )

async def serve():
    await db.apply_migrations()
    server = grpc.aio.server()
    payment_pb2_grpc.add_LedgerServiceServicer_to_server(LedgerService(), server)
    listen_addr = f"[::]:{LEDGER_GRPC_PORT}"
    server.add_insecure_port(listen_addr)
    logger.info(f"Ledger gRPC listening on {listen_addr}")
    await server.start()
    await server.wait_for_termination()

if __name__ == "__main__":
    asyncio.run(serve())
