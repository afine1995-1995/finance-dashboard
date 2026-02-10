"""Check if Mercury's global /transactions endpoint returns credit card transactions."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("MERCURY_API_TOKEN", "")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
BASE = "https://backend.mercury.com/api/v1"

# Try the global transactions endpoint (no account ID)
print("=== Global /transactions endpoint ===")
resp = requests.get(f"{BASE}/transactions", headers=headers,
                    params={"limit": 10, "order": "desc"}, timeout=30)
print(f"Status: {resp.status_code}")
if resp.ok:
    data = resp.json()
    txns = data.get("transactions", [])
    print(f"Got {len(txns)} transactions")
    # Check for unique account IDs
    acct_ids = set()
    for t in txns:
        aid = t.get("accountId", "unknown")
        acct_ids.add(aid)
        print(f"  {t.get('postedDate', t.get('createdAt', ''))[:10]}  "
              f"acct:{str(aid)[:12]}...  "
              f"{t.get('amount', 0):>10,.2f}  "
              f"{t.get('kind', ''):>15}  "
              f"{t.get('counterpartyName', '') or t.get('counterpartyNickname', '')}")
    print(f"\nUnique account IDs: {len(acct_ids)}")
    for aid in acct_ids:
        print(f"  {aid}")
else:
    print(f"Error: {resp.text[:500]}")

# Try the /credit endpoint
print("\n=== /credit endpoint ===")
resp = requests.get(f"{BASE}/credit", headers=headers, timeout=30)
print(f"Status: {resp.status_code}")
if resp.ok:
    print(resp.json())
else:
    print(f"Error: {resp.text[:500]}")

# Try /credit-cards endpoint
print("\n=== /credit-cards endpoint ===")
resp = requests.get(f"{BASE}/credit-cards", headers=headers, timeout=30)
print(f"Status: {resp.status_code}")
if resp.ok:
    print(resp.json())
else:
    print(f"Error: {resp.text[:300]}")

# Try /accounts with different params
print("\n=== /accounts?type=credit ===")
resp = requests.get(f"{BASE}/accounts", headers=headers,
                    params={"type": "credit"}, timeout=30)
print(f"Status: {resp.status_code}")
if resp.ok:
    accts = resp.json().get("accounts", [])
    print(f"Got {len(accts)} accounts")
    for a in accts:
        print(f"  {a.get('id')}  {a.get('name')}  type={a.get('type')}  kind={a.get('kind')}")
