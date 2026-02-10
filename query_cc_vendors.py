"""List all unique credit card vendors to verify categorization."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("MERCURY_API_TOKEN", "")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
BASE = "https://backend.mercury.com/api/v1"
CC_ID = "5b9c0980-0e24-11f0-8b96-9fe5f1206c4c"

# Fetch ALL credit card transactions
all_txns = []
offset = 0
while True:
    resp = requests.get(
        f"{BASE}/account/{CC_ID}/transactions",
        headers=headers,
        params={"offset": offset, "limit": 500, "start": "2020-01-01", "end": "2030-12-31"},
        timeout=30,
    )
    resp.raise_for_status()
    batch = resp.json().get("transactions", [])
    all_txns.extend(batch)
    if len(batch) < 500:
        break
    offset += 500

print(f"Total credit card transactions: {len(all_txns)}")

# Unique vendors with total spend
from collections import defaultdict
vendor_spend = defaultdict(float)
for t in all_txns:
    name = t.get("counterpartyName") or t.get("counterpartyNickname") or t.get("bankDescription", "")
    vendor_spend[name] += abs(t.get("amount", 0))

print(f"\nUnique vendors: {len(vendor_spend)}")
print("\nAll vendors (sorted by total spend):")
for name, total in sorted(vendor_spend.items(), key=lambda x: -x[1]):
    print(f"  ${total:>10,.2f}  {name}")
