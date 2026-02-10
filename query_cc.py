import sqlite3
conn = sqlite3.connect(r"C:\Users\afine\finance-dashboard\finance.db")
conn.row_factory = sqlite3.Row

# Show all accounts and transaction counts
print("=== ACCOUNTS ===")
rows = conn.execute("""
    SELECT account_id, COUNT(*) as cnt,
           SUM(CASE WHEN amount < 0 THEN 1 ELSE 0 END) as outflows,
           SUM(CASE WHEN amount > 0 THEN 1 ELSE 0 END) as inflows
    FROM mercury_transactions
    GROUP BY account_id
""").fetchall()
for r in rows:
    print(f"  {r['account_id']}  —  {r['cnt']} txns ({r['outflows']} out, {r['inflows']} in)")

# Check if any account looks like a credit card (lots of small outflows)
print("\n=== CREDIT CARD CANDIDATES (accounts with 'credit' or 'card' in transactions) ===")
rows = conn.execute("""
    SELECT DISTINCT account_id FROM mercury_transactions
    WHERE counterparty_name LIKE '%Mercury Credit%'
       OR counterparty_name LIKE '%Credit Card%'
       OR kind LIKE '%credit%'
""").fetchall()
for r in rows:
    print(f"  {r['account_id']}")

# Show transactions from accounts that have Mercury Credit as counterparty
print("\n=== TRANSACTIONS WHERE COUNTERPARTY IS 'Mercury Credit' ===")
rows = conn.execute("""
    SELECT account_id, counterparty_name, amount, kind,
           COALESCE(posted_date, created_at) as dt
    FROM mercury_transactions
    WHERE counterparty_name LIKE 'Mercury Credit%'
    ORDER BY dt DESC
    LIMIT 10
""").fetchall()
for r in rows:
    print(f"  {r['dt']}  {r['amount']:>12,.2f}  {r['kind']}  {r['counterparty_name']}  (acct: {r['account_id'][:12]}...)")

# For each account, show sample counterparties
print("\n=== SAMPLE COUNTERPARTIES BY ACCOUNT ===")
acct_rows = conn.execute("SELECT DISTINCT account_id FROM mercury_transactions").fetchall()
for acct in acct_rows:
    aid = acct['account_id']
    print(f"\n  Account {aid[:16]}...")
    samples = conn.execute("""
        SELECT counterparty_name, amount, kind
        FROM mercury_transactions
        WHERE account_id = ? AND amount < 0
        ORDER BY COALESCE(posted_date, created_at) DESC
        LIMIT 15
    """, (aid,)).fetchall()
    for s in samples:
        print(f"    {s['amount']:>10,.2f}  {s['kind'] or '':>12}  {s['counterparty_name']}")

conn.close()
