CREATE TABLE IF NOT EXISTS mercury_transactions (
    id TEXT PRIMARY KEY,
    amount REAL NOT NULL,
    counterparty_name TEXT,
    note TEXT,
    kind TEXT,
    status TEXT,
    created_at TEXT,
    posted_date TEXT,
    account_id TEXT
);

CREATE TABLE IF NOT EXISTS stripe_invoices (
    id TEXT PRIMARY KEY,
    number TEXT,
    customer_id TEXT,
    customer_name TEXT,
    customer_email TEXT,
    amount_due REAL NOT NULL,
    amount_paid REAL NOT NULL DEFAULT 0,
    currency TEXT DEFAULT 'usd',
    status TEXT,
    due_date TEXT,
    created_at TEXT,
    paid_at TEXT,
    hosted_invoice_url TEXT
);

CREATE TABLE IF NOT EXISTS stripe_subscriptions (
    id TEXT PRIMARY KEY,
    customer_id TEXT,
    customer_name TEXT,
    status TEXT,
    monthly_amount REAL NOT NULL DEFAULT 0,
    currency TEXT DEFAULT 'usd',
    current_period_start TEXT,
    current_period_end TEXT
);

CREATE TABLE IF NOT EXISTS late_payment_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id TEXT NOT NULL,
    notified_at TEXT NOT NULL,
    email_sent INTEGER NOT NULL DEFAULT 0,
    email_sent_at TEXT,
    UNIQUE(invoice_id)
);

CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    synced_at TEXT NOT NULL,
    records_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'success',
    error_message TEXT
);
