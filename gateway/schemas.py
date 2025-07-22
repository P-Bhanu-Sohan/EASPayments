from pydantic import BaseModel, Field, validator
from typing import Optional

class TransferIn(BaseModel):
    from_account: str = Field(..., description="UUID of source account")
    to_account: str = Field(..., description="UUID of destination account")
    amount: int = Field(..., ge=1, description="Minor units (paise)")
    currency: str = Field("INR")
    idempotency_key: str = Field(..., min_length=1, max_length=128)

    @validator("to_account")
    def accounts_must_differ(cls, v, values):
        if "from_account" in values and v == values["from_account"]:
            raise ValueError("from_account and to_account must differ")
        return v

class TransferOut(BaseModel):
    tx_id: str
    from_account: str
    to_account: str
    amount: int
    currency: str
    from_balance_after: int
    to_balance_after: int
    status: str
    message: str | None = None

class BalanceOut(BaseModel):
    account_id: str
    balance: int
    currency: str
