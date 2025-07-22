import grpc

from .config import settings

# generated stubs live in gateway/ (installed at build step)
from . import payment_pb2
from . import payment_pb2_grpc

_ledger_channel = None
_ledger_stub = None
_notify_channel = None
_notify_stub = None

async def get_ledger_stub():
    global _ledger_channel, _ledger_stub
    if _ledger_stub is None:
        _ledger_channel = grpc.aio.insecure_channel(settings.ledger_grpc_target)
        _ledger_stub = payment_pb2_grpc.LedgerServiceStub(_ledger_channel)
    return _ledger_stub

async def get_notify_stub():
    global _notify_channel, _notify_stub
    if _notify_stub is None:
        _notify_channel = grpc.aio.insecure_channel(settings.notify_grpc_target)
        _notify_stub = payment_pb2_grpc.NotificationServiceStub(_notify_channel)
    return _notify_stub

async def ledger_transfer(**kwargs):
    stub = await get_ledger_stub()
    req = payment_pb2.TransferRequest(**kwargs)
    resp = await stub.Transfer(req)
    return resp

async def ledger_get_balance(account_id: str):
    stub = await get_ledger_stub()
    req = payment_pb2.BalanceRequest(account_id=account_id)
    resp = await stub.GetBalance(req)
    return resp

async def ledger_get_all_entries():
    stub = await get_ledger_stub()
    req = payment_pb2.GetAllRequest()
    resp = await stub.GetAllEntries(req)
    return resp

async def send_notification(account_id: str, tx_id: str, amount: int, direction: str, currency: str, message: str):
    stub = await get_notify_stub()
    req = payment_pb2.NotificationRequest(
        account_id=account_id,
        tx_id=tx_id,
        amount=amount,
        direction=direction,
        currency=currency,
        message=message,
    )
    await stub.Notify(req)
