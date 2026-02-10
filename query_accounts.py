"""Temporary script to inspect Mercury accounts via API."""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("MERCURY_API_TOKEN", "")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

resp = requests.get("https://backend.mercury.com/api/v1/accounts", headers=headers, timeout=30)
resp.raise_for_status()
accounts = resp.json().get("accounts", [])

print(f"Found {len(accounts)} accounts:\n")
for acct in accounts:
    print(f"  ID:   {acct.get('id')}")
    print(f"  Name: {acct.get('name')}")
    print(f"  Type: {acct.get('type')}")
    print(f"  Kind: {acct.get('kind')}")
    print(f"  Status: {acct.get('status')}")
    print(f"  Balance: {acct.get('currentBalance')}")
    print()

# If there's a credit card account, fetch a few transactions
for acct in accounts:
    acct_type = (acct.get("type") or "").lower()
    acct_kind = (acct.get("kind") or "").lower()
    acct_name = (acct.get("name") or "").lower()
    if "credit" in acct_type or "credit" in acct_kind or "credit" in acct_name:
        print(f"\n=== CREDIT CARD ACCOUNT: {acct['name']} ({acct['id']}) ===")
        txn_resp = requests.get(
            f"https://backend.mercury.com/api/v1/account/{acct['id']}/transactions",
            headers=headers,
            params={"limit": 20},
            timeout=30,
        )
        txn_resp.raise_for_status()
        txns = txn_resp.json().get("transactions", [])
        print(f"  Sample transactions ({len(txns)}):")
        for t in txns:
            print(f"    {t.get('postedDate', t.get('createdAt', ''))[:10]}  "
                  f"{t.get('amount', 0):>10,.2f}  "
                  f"{t.get('kind', ''):>15}  "
                  f"{t.get('counterpartyName', '') or t.get('counterpartyNickname', '')}")
