"""Quick script to verify credit card data in the spending chart."""
import sys
sys.path.insert(0, ".")

from models.database import get_connection
from models.queries import get_monthly_spend_by_category

conn = get_connection()
row = conn.execute("""
    SELECT COUNT(*) as cnt FROM mercury_transactions
    WHERE kind = 'creditCardTransaction' OR kind = 'cardInternationalTransactionFee'
""").fetchone()
print(f"Credit card transactions in DB: {row['cnt']}")
conn.close()

data = get_monthly_spend_by_category()
print(f"\nMonths with credit card spend data: {len(data)}")
for month in sorted(data.keys()):
    total = sum(data[month].values())
    cats = {k: v for k, v in data[month].items() if v > 0}
    print(f"  {month}: ${total:,.0f}  {cats}")
