import logging

import requests

from config import Config
from models.queries import upsert_mercury_transaction, log_sync

logger = logging.getLogger(__name__)

BASE_URL = "https://backend.mercury.com/api/v1"


def _headers():
    return {
        "Authorization": f"Bearer {Config.MERCURY_API_TOKEN}",
        "Content-Type": "application/json",
    }


def _get_accounts():
    """Fetch all Mercury accounts."""
    resp = requests.get(f"{BASE_URL}/accounts", headers=_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json().get("accounts", [])


def _get_transactions(account_id: str):
    """Fetch all transactions for a Mercury account, handling pagination."""
    transactions = []
    offset = 0
    limit = 500

    while True:
        resp = requests.get(
            f"{BASE_URL}/account/{account_id}/transactions",
            headers=_headers(),
            params={"offset": offset, "limit": limit, "start": "2020-01-01", "end": "2030-12-31"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        batch = data.get("transactions", [])
        transactions.extend(batch)

        if len(batch) < limit:
            break
        offset += limit

    return transactions


def _get_credit_accounts():
    """Fetch Mercury credit card accounts via /credit endpoint."""
    resp = requests.get(f"{BASE_URL}/credit", headers=_headers(), timeout=30)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    return resp.json().get("accounts", [])


def get_total_balance() -> float:
    """Fetch the total balance across all Mercury accounts."""
    try:
        accounts = _get_accounts()
        total = sum(a.get("currentBalance", 0) for a in accounts)
        return total
    except Exception as e:
        logger.error(f"Failed to fetch Mercury balance: {e}")
        return 0


def sync_transactions():
    """Fetch all Mercury transactions across all accounts (including credit card) and cache in SQLite."""
    logger.info("Syncing Mercury transactions...")
    count = 0
    try:
        # Gather all account IDs: checking/savings + credit card
        account_ids = []
        accounts = _get_accounts()
        for account in accounts:
            account_ids.append(account["id"])

        credit_accounts = _get_credit_accounts()
        for ca in credit_accounts:
            account_ids.append(ca["id"])

        for account_id in account_ids:
            transactions = _get_transactions(account_id)

            for txn in transactions:
                counterparty = txn.get("counterpartyName", "")
                if not counterparty and txn.get("counterpartyNickname"):
                    counterparty = txn["counterpartyNickname"]

                upsert_mercury_transaction({
                    "id": txn["id"],
                    "amount": txn["amount"],
                    "counterparty_name": counterparty,
                    "note": txn.get("note"),
                    "kind": txn.get("kind"),
                    "status": txn.get("status"),
                    "created_at": txn.get("createdAt"),
                    "posted_date": txn.get("postedDate"),
                    "account_id": account_id,
                })
                count += 1

        log_sync("mercury", count)
        logger.info(f"Synced {count} Mercury transactions")
    except Exception as e:
        logger.error(f"Mercury sync failed: {e}")
        log_sync("mercury", count, status="error", error_message=str(e))
        raise

    return count
