"""Verify we can pull credit card transactions and see sample data."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("MERCURY_API_TOKEN", "")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
BASE = "https://backend.mercury.com/api/v1"

CC_ID = "5b9c0980-0e24-11f0-8b96-9fe5f1206c4c"

# Try /account/{cc_id}/transactions
print("=== Credit card transactions via /account/{id}/transactions ===")
resp = requests.get(f"{BASE}/account/{CC_ID}/transactions",
                    headers=headers,
                    params={"limit": 50, "start": "2025-01-01", "end": "2030-12-31"},
                    timeout=30)
print(f"Status: {resp.status_code}")
if resp.ok:
    txns = resp.json().get("transactions", [])
    print(f"Got {len(txns)} transactions")
    for t in txns[:30]:
        print(f"  {t.get('postedDate', t.get('createdAt', ''))[:10]}  "
              f"{t.get('amount', 0):>10,.2f}  "
              f"{t.get('kind', ''):>20}  "
              f"{t.get('counterpartyName', '') or t.get('counterpartyNickname', '') or t.get('bankDescription', '')}")
else:
    # If direct account endpoint fails, use global with filter
    print(f"Direct endpoint failed: {resp.text[:300]}")
    print("\n=== Trying global /transactions with accountId filter ===")
    resp = requests.get(f"{BASE}/transactions",
                        headers=headers,
                        params={"limit": 50, "order": "desc", "accountId": CC_ID},
                        timeout=30)
    print(f"Status: {resp.status_code}")
    if resp.ok:
        txns = resp.json().get("transactions", [])
        print(f"Got {len(txns)} transactions")
        for t in txns[:30]:
            print(f"  {t.get('postedDate', t.get('createdAt', ''))[:10]}  "
                  f"{t.get('amount', 0):>10,.2f}  "
                  f"{t.get('kind', ''):>20}  "
                  f"{t.get('counterpartyName', '') or t.get('counterpartyNickname', '') or t.get('bankDescription', '')}")
