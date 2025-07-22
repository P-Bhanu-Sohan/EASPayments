CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR',
    start_balance BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ledger_entries (
    id BIGSERIAL PRIMARY KEY,
    tx_id TEXT NOT NULL,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    direction TEXT NOT NULL CHECK (direction IN ('DEBIT','CREDIT')),
    amount BIGINT NOT NULL CHECK (amount > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ledger_acct ON ledger_entries(account_id);
CREATE INDEX IF NOT EXISTS idx_ledger_tx ON ledger_entries(tx_id);

CREATE TABLE IF NOT EXISTS idempotency_keys (
    key TEXT PRIMARY KEY,
    tx_id TEXT,
    status TEXT NOT NULL DEFAULT 'IN_PROGRESS',
    response JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
