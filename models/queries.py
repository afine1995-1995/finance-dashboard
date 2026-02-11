from datetime import datetime, timezone

from models.database import get_connection

# SQL clause to exclude internal/self transfers and owner draws
EXCLUDE_INTERNAL = """
    AND counterparty_name NOT LIKE '%Wells Fargo%0430%'
    AND counterparty_name NOT LIKE '%Bank of America%1717%'
    AND counterparty_name NOT LIKE 'BANK OF AMERICA'
    AND counterparty_name NOT LIKE '%Chase%'
    AND counterparty_name NOT LIKE 'Mercury Checking%'
    AND counterparty_name NOT LIKE 'Mercury Savings%'
    AND counterparty_name NOT LIKE 'Mercury Credit%'
    AND counterparty_name NOT LIKE 'Mercury IO%'
    AND counterparty_name != 'Alex Fine'
    AND counterparty_name != 'Alexander Yildirim'
"""

# SQL clause matching owner distribution counterparties
OWNER_DISTRIBUTIONS = """
    (counterparty_name LIKE '%Wells Fargo%0430%'
     OR counterparty_name LIKE '%Bank of America%1717%'
     OR counterparty_name = 'BANK OF AMERICA'
     OR counterparty_name = 'Alex Fine'
     OR counterparty_name = 'Alexander Yildirim')
"""


# --------------- Spend Categories ---------------

def categorize_vendor(name, kind=None):
    """Categorize a counterparty name into a spending category.

    Args:
        name: Counterparty name.
        kind: Mercury transaction kind. If 'outgoingPayment', unmatched
              vendors default to Labor (contractors) instead of Miscellaneous.
    """
    if not name:
        return "Miscellaneous"
    upper = name.upper()

    # Salaries — ADP payroll
    if upper.startswith("ADP"):
        return "Salaries"

    # Taxes — IRS, state taxes, tax/accounting firms
    if any(kw in upper for kw in [
        "IRS", "GEORGIA ITS TAX", "GA DEPT OF LABOR",
        "BOYLE TAX", "SAVERITE TAX", "STATE OF TN",
        "DELAWARE CORP",
    ]):
        return "Taxes"

    # Email Infrastructure — premium inboxes, email sending, email domains
    if upper.startswith("RMT*"):
        return "Email Infrastructure"
    if any(kw in upper for kw in [
        "BEANSTALK CONSULTING", "INBOXKIT", "PREMIUM INBOX",
        "MISSION INBOX", "OUTBOUNDSYNC", "COLDEMAILDOMAINS",
        "BOUNCEBAN", "MAILTESTER",
    ]):
        return "Email Infrastructure"

    # Travel — airlines, hotels, rideshare, parking
    if any(kw in upper for kw in [
        "AIRLINE", "DELTA AIR", "UNITED AIR", "AMERICAN AIR", "SOUTHWEST",
        "TURKISH AIR", "HOTEL", "MARRIOTT", "HILTON", "AIRBNB", "UBER",
        "LYFT", "WAYMO", "TRAVELURO", "HOTELS.COM", "THE PEARL",
        "DIPLOMAT", "RITZ-CARLTON", "CANOPY BY HILTON", "MOTTO BY HILTON",
        "PARKING", "OWLPARKING", "12 OAKS",
    ]):
        return "Travel"

    # Tech Vendors — software, SaaS, AI, sales tools, lead gen, ads
    if any(kw in upper for kw in [
        "GROWTHX", "STRIPE", "OPENAI", "OPEN AI", "CHATGPT", "ANTHROPIC",
        "CLAUDE", "LOVABLE", "MANUS", "GITHUB", "GOOGLE", "MICROSOFT",
        "AMAZON WEB", "AWS", "HEROKU", "VERCEL", "NETLIFY", "DIGITAL OCEAN",
        "CLOUDFLARE", "SLACK", "NOTION", "FIGMA", "CANVA", "HUBSPOT",
        "SALESFORCE", "ZAPIER", "AIRTABLE", "CLICKUP", "ZOOM", "LOOM",
        "LINKEDIN", "FACEBOOK", "FACEBK", "CLAY LABS", "INSTANTLY",
        "HEYREACH", "FIREFLIES", "PANDADOC", "MIRO", "CALENDLY",
        "ATLASSIAN", "BEEHIIV", "MAKE", "WISPR", "SUPERMETRICS",
        "QUICKBOOKS", "1PASSWORD", "SUPABASE", "CURSOR", "APIFY",
        "RAILWAY", "GAMMA", "TELLA", "WP ENGINE", "PORTER METRICS",
        "PERPLEXITY", "SQUARESPACE", "BOOMERANG", "RIVERSIDE",
        "CHECKR", "NAMECHEAP", "PERSONA", "PORKBUN", "SERPER",
        "OTTERAD", "TRADEMIMIC", "KIIN", "ENRICH LABS", "KS-MEDIA",
        "STORE LEADS", "TEAMFLUENCE", "LEADSFRIDAY", "LEADWAVE",
        "AMPLELEADS", "LEADS ON TREES", "FOLLOWINGG", "ENGAGERS",
        "AI ARK", "TRYKITT", "OVERVUE", "UPSCALE SYSTEMS",
        "SALES AUTOMATION", "THEIRSTACK", "MERGR", "LEADASSIST",
        "DEMANDGEN", "AI.FYXER", "SUPERHOG", "AMAZON PRIME",
        "VIASAT", "FIBBLER", "OCTAVE",
    ]):
        return "Tech Vendors"

    # Labor — consulting, agencies, services
    if any(kw in upper for kw in [
        "FUELFINANCE", "AUTOMATEDEMAND", "FANBASIS", "PAYONEER",
        "REVPARTNERS", "VIVA GROWTH", "CHITLANGIA", "NOAH GREEN",
        "COASTAL-COLLECTIVE", "LA WHENCE",
    ]):
        return "Labor"

    # Outgoing payments from checking are contractor/labor payments
    if kind == "outgoingPayment":
        return "Labor"

    # Miscellaneous — food, health, entertainment, everything else
    return "Miscellaneous"


SPEND_CATEGORIES = [
    "Salaries",
    "Labor",
    "Tech Vendors",
    "Email Infrastructure",
    "Taxes",
    "Travel",
    "Miscellaneous",
]


# --------------- Mercury Transactions ---------------

def upsert_mercury_transaction(txn: dict):
    conn = get_connection()
    conn.execute(
        """INSERT INTO mercury_transactions
               (id, amount, counterparty_name, note, kind, status, created_at, posted_date, account_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET
               amount=excluded.amount,
               counterparty_name=excluded.counterparty_name,
               note=excluded.note,
               kind=excluded.kind,
               status=excluded.status,
               created_at=excluded.created_at,
               posted_date=excluded.posted_date,
               account_id=excluded.account_id""",
        (
            txn["id"],
            txn["amount"],
            txn.get("counterparty_name"),
            txn.get("note"),
            txn.get("kind"),
            txn.get("status"),
            txn.get("created_at"),
            txn.get("posted_date"),
            txn.get("account_id"),
        ),
    )
    conn.commit()
    conn.close()


def get_mercury_monthly_flows():
    """Return monthly inflow/outflow totals and owner distributions.

    Excludes credit card transactions to avoid double-counting (the lump
    payment from checking to Mercury Credit is already excluded via
    EXCLUDE_INTERNAL).
    """
    conn = get_connection()
    rows = conn.execute(
        f"""SELECT
               strftime('%Y-%m', COALESCE(posted_date, created_at)) AS month,
               SUM(CASE WHEN amount > 0 {EXCLUDE_INTERNAL} THEN amount ELSE 0 END) AS inflows,
               SUM(CASE WHEN amount < 0 {EXCLUDE_INTERNAL} THEN ABS(amount) ELSE 0 END) AS outflows,
               SUM(CASE WHEN amount < 0 AND {OWNER_DISTRIBUTIONS} THEN ABS(amount) ELSE 0 END) AS owner_distributions
           FROM mercury_transactions
           WHERE COALESCE(posted_date, created_at) IS NOT NULL
             AND status NOT IN ('cancelled', 'failed')
             AND kind NOT IN ('creditCardTransaction', 'cardInternationalTransactionFee')
           GROUP BY month
           ORDER BY month"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_mercury_inflows_over_time():
    """Return monthly inflows for the line chart, excluding internal transfers."""
    conn = get_connection()
    rows = conn.execute(
        f"""SELECT
               strftime('%Y-%m', COALESCE(posted_date, created_at)) AS month,
               SUM(amount) AS total
           FROM mercury_transactions
           WHERE amount > 0
             AND COALESCE(posted_date, created_at) IS NOT NULL
             AND status NOT IN ('cancelled', 'failed')
             AND kind NOT IN ('creditCardTransaction', 'cardInternationalTransactionFee')
             {EXCLUDE_INTERNAL}
           GROUP BY month
           ORDER BY month"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --------------- Stripe Invoices ---------------

def upsert_stripe_invoice(inv: dict):
    conn = get_connection()
    conn.execute(
        """INSERT INTO stripe_invoices
               (id, number, customer_id, customer_name, customer_email,
                amount_due, amount_paid, currency, status, due_date, created_at, paid_at, hosted_invoice_url)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET
               number=excluded.number,
               customer_id=excluded.customer_id,
               customer_name=excluded.customer_name,
               customer_email=excluded.customer_email,
               amount_due=excluded.amount_due,
               amount_paid=excluded.amount_paid,
               currency=excluded.currency,
               status=excluded.status,
               due_date=excluded.due_date,
               created_at=excluded.created_at,
               paid_at=excluded.paid_at,
               hosted_invoice_url=excluded.hosted_invoice_url""",
        (
            inv["id"],
            inv.get("number"),
            inv.get("customer_id"),
            inv.get("customer_name"),
            inv.get("customer_email"),
            inv["amount_due"],
            inv.get("amount_paid", 0),
            inv.get("currency", "usd"),
            inv.get("status"),
            inv.get("due_date"),
            inv.get("created_at"),
            inv.get("paid_at"),
            inv.get("hosted_invoice_url"),
        ),
    )
    conn.commit()
    conn.close()


def get_late_invoices():
    """Return open invoices past due date that haven't been notified yet."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = get_connection()
    rows = conn.execute(
        """SELECT si.*
           FROM stripe_invoices si
           LEFT JOIN late_payment_notifications lpn ON si.id = lpn.invoice_id
           WHERE si.status = 'open'
             AND si.due_date < ?
             AND si.amount_due > 0
             AND lpn.invoice_id IS NULL
           ORDER BY si.due_date""",
        (now,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_late_invoices():
    """Return all open invoices past due (regardless of notification status)."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = get_connection()
    rows = conn.execute(
        """SELECT si.*
           FROM stripe_invoices si
           WHERE si.status = 'open'
             AND si.due_date < ?
             AND si.amount_due > 0
           ORDER BY si.due_date""",
        (now,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_invoice_by_id(invoice_id: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM stripe_invoices WHERE id = ?", (invoice_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def mark_notified(invoice_id: str):
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    conn.execute(
        """INSERT INTO late_payment_notifications (invoice_id, notified_at)
           VALUES (?, ?)
           ON CONFLICT(invoice_id) DO NOTHING""",
        (invoice_id, now),
    )
    conn.commit()
    conn.close()


def mark_email_sent(invoice_id: str):
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    conn.execute(
        """UPDATE late_payment_notifications
           SET email_sent = 1, email_sent_at = ?
           WHERE invoice_id = ?""",
        (now, invoice_id),
    )
    conn.commit()
    conn.close()


# --------------- Stripe Subscriptions ---------------

def upsert_stripe_subscription(sub: dict):
    conn = get_connection()
    conn.execute(
        """INSERT INTO stripe_subscriptions
               (id, customer_id, customer_name, status, monthly_amount, currency,
                current_period_start, current_period_end)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET
               customer_id=excluded.customer_id,
               customer_name=excluded.customer_name,
               status=excluded.status,
               monthly_amount=excluded.monthly_amount,
               currency=excluded.currency,
               current_period_start=excluded.current_period_start,
               current_period_end=excluded.current_period_end""",
        (
            sub["id"],
            sub.get("customer_id"),
            sub.get("customer_name"),
            sub.get("status"),
            sub["monthly_amount"],
            sub.get("currency", "usd"),
            sub.get("current_period_start"),
            sub.get("current_period_end"),
        ),
    )
    conn.commit()
    conn.close()


def _has_subscriptions():
    """Check if the stripe_subscriptions table has any active data."""
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM stripe_subscriptions WHERE status = 'active'"
    ).fetchone()
    conn.close()
    return row["cnt"] > 0


def _get_active_client_ids():
    """Return set of customer_ids that are currently active.

    Uses subscriptions table if populated, otherwise falls back to
    clients invoiced in the last 90 days.
    """
    conn = get_connection()
    if _has_subscriptions():
        rows = conn.execute(
            """SELECT DISTINCT customer_id FROM stripe_subscriptions
               WHERE status = 'active' AND customer_id IS NOT NULL"""
        ).fetchall()
    else:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        rows = conn.execute(
            """SELECT DISTINCT customer_id FROM stripe_invoices
               WHERE status IN ('paid', 'open')
                 AND created_at >= date(?, '-90 days')
                 AND customer_id IS NOT NULL""",
            (now,),
        ).fetchall()
    conn.close()
    return {r["customer_id"] for r in rows}


def get_active_subscriptions_by_client():
    """Return current active clients with monthly revenue.

    Combines two sources:
    1. Stripe active subscriptions (monthly_amount from subscription items)
    2. Mercury direct payers (clients who pay via wire/ACH, not through Stripe)

    Mercury direct payers are identified from inflows in the last 90 days,
    excluding Stripe payouts, internal transfers, and non-client amounts.
    Their monthly revenue is calculated as total / number of months active.
    """
    conn = get_connection()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    clients = {}  # {name: monthly_revenue}

    # 1. Stripe active subscriptions
    if _has_subscriptions():
        rows = conn.execute(
            """SELECT customer_name,
                   SUM(monthly_amount) AS monthly_revenue
               FROM stripe_subscriptions
               WHERE status = 'active'
                 AND customer_name IS NOT NULL
               GROUP BY customer_name"""
        ).fetchall()
        for r in rows:
            if r["monthly_revenue"] and r["monthly_revenue"] > 0:
                clients[r["customer_name"]] = r["monthly_revenue"]

    # 2. Mercury direct payers (last 90 days, excluding Stripe payouts and internal)
    rows = conn.execute(
        f"""SELECT counterparty_name,
               SUM(amount) AS total,
               COUNT(DISTINCT strftime('%%Y-%%m', COALESCE(posted_date, created_at))) AS months_active
           FROM mercury_transactions
           WHERE amount > 0
             AND COALESCE(posted_date, created_at) >= date(?, '-90 days')
             AND status NOT IN ('cancelled', 'failed')
             AND kind NOT IN ('creditCardTransaction', 'cardInternationalTransactionFee')
             AND counterparty_name != 'STRIPE'
             AND counterparty_name NOT LIKE 'Savings Interest%'
             AND counterparty_name NOT LIKE '%Cashback%'
             AND counterparty_name NOT LIKE '%ANTHEM%'
             AND counterparty_name NOT LIKE '%Kaiser%'
             AND counterparty_name NOT LIKE '%JP Morgan%'
             {EXCLUDE_INTERNAL}
           GROUP BY counterparty_name
           HAVING total >= 1000""",
        (now,),
    ).fetchall()

    for r in rows:
        name = r["counterparty_name"]
        months = max(r["months_active"], 1)
        monthly = round(r["total"] / months, 2)
        # Add to existing (unlikely overlap) or set
        clients[name] = clients.get(name, 0) + monthly

    conn.close()

    # Sort by monthly revenue descending
    results = [
        {"customer_name": name, "monthly_revenue": rev}
        for name, rev in sorted(clients.items(), key=lambda x: -x[1])
    ]
    return results


# --------------- Stripe Analytics ---------------

def get_avg_days_to_pay():
    """Return average days to pay for active clients only.

    Sorted slowest payers first (descending by avg_days).
    Uses subscriptions for filtering if available, otherwise recent invoices.
    """
    active_ids = _get_active_client_ids()

    if not active_ids:
        return []

    placeholders = ",".join("?" for _ in active_ids)
    conn = get_connection()
    rows = conn.execute(
        f"""SELECT customer_name,
               ROUND(AVG(julianday(paid_at) - julianday(created_at)), 1) AS avg_days,
               COUNT(*) AS invoice_count
           FROM stripe_invoices
           WHERE status = 'paid'
             AND paid_at IS NOT NULL
             AND customer_name IS NOT NULL
             AND customer_id IN ({placeholders})
           GROUP BY customer_name
           ORDER BY avg_days DESC""",
        list(active_ids),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_overall_avg_days_to_pay():
    """Return overall average days to pay across all paid invoices."""
    conn = get_connection()
    row = conn.execute(
        """SELECT ROUND(AVG(julianday(paid_at) - julianday(created_at)), 1) AS avg_days,
               COUNT(*) AS total_invoices
           FROM stripe_invoices
           WHERE status = 'paid'
             AND paid_at IS NOT NULL"""
    ).fetchone()
    conn.close()
    return dict(row) if row else {"avg_days": 0, "total_invoices": 0}


def get_revenue_by_client():
    """Return total paid revenue by client, sorted by amount descending."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT customer_name,
               SUM(amount_paid) AS total_revenue,
               COUNT(*) AS invoice_count
           FROM stripe_invoices
           WHERE amount_paid > 0
             AND customer_name IS NOT NULL
           GROUP BY customer_name
           ORDER BY total_revenue DESC"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --------------- Spend by Category ---------------

# Only successful transactions (exclude failed, cancelled, reversed)
VALID_STATUS = "AND status = 'sent'"

# Credit card itemized purchases (excludes balance payments to checking)
CREDIT_CARD_FILTER = """
    AND (kind = 'creditCardTransaction' OR kind = 'cardInternationalTransactionFee')
    AND counterparty_name NOT LIKE 'Mercury Checking%'
"""

# Checking account labor payments (contractors, freelancers), excluding owners
LABOR_FILTER = """
    AND kind = 'outgoingPayment'
    AND counterparty_name != 'Alex Fine'
    AND counterparty_name != 'Alexander Yildirim'
"""

# Checking/savings account operational costs (salaries, taxes, labor via Payoneer)
CHECKING_OPS_FILTER = f"""
    AND kind = 'other'
    AND (counterparty_name LIKE 'ADP%'
         OR counterparty_name LIKE '%IRS%'
         OR counterparty_name LIKE '%GEORGIA ITS TAX%'
         OR counterparty_name LIKE '%GA DEPT OF LABOR%'
         OR counterparty_name LIKE '%BOYLE TAX%'
         OR counterparty_name LIKE '%SAVERITE TAX%'
         OR counterparty_name LIKE '%STATE OF TN%'
         OR counterparty_name LIKE '%DELAWARE CORP%'
         OR counterparty_name LIKE '%Payoneer%')
    {EXCLUDE_INTERNAL}
"""


def _query_spend_rows(conn, extra_filter):
    """Run a spend query with the given filter, returning rows with kind."""
    return conn.execute(
        f"""SELECT
               strftime('%Y-%m', COALESCE(posted_date, created_at)) AS month,
               counterparty_name,
               kind,
               SUM(ABS(amount)) AS total
           FROM mercury_transactions
           WHERE amount < 0
             AND COALESCE(posted_date, created_at) IS NOT NULL
             {VALID_STATUS}
             {extra_filter}
           GROUP BY month, counterparty_name, kind
           ORDER BY month, total DESC"""
    ).fetchall()


def get_monthly_spend_by_category():
    """Return monthly spending broken down by category.

    Combines:
    - Credit card itemized transactions (tech, email infra, travel, misc)
    - Checking account outgoing payments (labor/contractors)
    - Checking account ADP/tax payments (salaries, taxes)

    Returns dict: {month: {category: amount}}.
    """
    conn = get_connection()

    all_rows = []
    all_rows.extend(_query_spend_rows(conn, CREDIT_CARD_FILTER))
    all_rows.extend(_query_spend_rows(conn, LABOR_FILTER))
    all_rows.extend(_query_spend_rows(conn, CHECKING_OPS_FILTER))
    conn.close()

    result = {}
    for r in all_rows:
        month = r["month"]
        category = categorize_vendor(r["counterparty_name"], r["kind"])
        if month not in result:
            result[month] = {c: 0 for c in SPEND_CATEGORIES}
        result[month][category] = result[month].get(category, 0) + r["total"]

    return result


def get_monthly_spend_details():
    """Return monthly spending with vendor-level detail for hover info.

    Combines credit card, labor, and checking ops transactions.
    Returns dict: {month: {category: [(vendor, amount), ...]}}.
    """
    conn = get_connection()

    all_rows = []
    all_rows.extend(_query_spend_rows(conn, CREDIT_CARD_FILTER))
    all_rows.extend(_query_spend_rows(conn, LABOR_FILTER))
    all_rows.extend(_query_spend_rows(conn, CHECKING_OPS_FILTER))
    conn.close()

    result = {}
    for r in all_rows:
        month = r["month"]
        category = categorize_vendor(r["counterparty_name"], r["kind"])
        if month not in result:
            result[month] = {c: [] for c in SPEND_CATEGORIES}
        result[month].setdefault(category, []).append(
            (r["counterparty_name"], r["total"])
        )

    return result


# --------------- Open Invoices ---------------

def get_open_invoices_for_client(customer_name: str):
    """Return all open invoices for a specific client, with email_sent status."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT si.id, si.number, si.customer_email, si.amount_due,
                  si.due_date, si.hosted_invoice_url,
                  COALESCE(lpn.email_sent, 0) AS email_sent
           FROM stripe_invoices si
           LEFT JOIN late_payment_notifications lpn ON si.id = lpn.invoice_id
           WHERE si.status = 'open'
             AND si.amount_due > 0
             AND si.customer_name = ?
           ORDER BY si.due_date""",
        (customer_name,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_open_invoices_by_client():
    """Return open invoices grouped by client, split into outstanding vs overdue."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = get_connection()
    rows = conn.execute(
        """SELECT customer_name,
               SUM(CASE WHEN due_date >= ? OR due_date IS NULL THEN amount_due ELSE 0 END) AS outstanding,
               SUM(CASE WHEN due_date < ? THEN amount_due ELSE 0 END) AS overdue
           FROM stripe_invoices
           WHERE status = 'open'
             AND amount_due > 0
             AND customer_name IS NOT NULL
           GROUP BY customer_name
           ORDER BY (outstanding + overdue) DESC""",
        (now, now),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --------------- Sync Log ---------------

def log_sync(source: str, records_count: int, status: str = "success", error_message: str = None):
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    conn.execute(
        """INSERT INTO sync_log (source, synced_at, records_count, status, error_message)
           VALUES (?, ?, ?, ?, ?)""",
        (source, now, records_count, status, error_message),
    )
    conn.commit()
    conn.close()


# --------------- Summary helpers ---------------

def get_period_summary(start_date: str, end_date: str):
    """Get financial summary for a date range."""
    conn = get_connection()
    mercury = conn.execute(
        f"""SELECT
               SUM(CASE WHEN amount > 0 {EXCLUDE_INTERNAL} THEN amount ELSE 0 END) AS inflows,
               SUM(CASE WHEN amount < 0 {EXCLUDE_INTERNAL} THEN ABS(amount) ELSE 0 END) AS outflows
           FROM mercury_transactions
           WHERE COALESCE(posted_date, created_at) BETWEEN ? AND ?
             AND status NOT IN ('cancelled', 'failed')
             AND kind NOT IN ('creditCardTransaction', 'cardInternationalTransactionFee')""",
        (start_date, end_date),
    ).fetchone()

    late_count = conn.execute(
        """SELECT COUNT(*) AS cnt
           FROM stripe_invoices
           WHERE status = 'open'
             AND due_date < ?
             AND amount_due > 0""",
        (end_date,),
    ).fetchone()

    top_customers = conn.execute(
        """SELECT customer_name, SUM(amount_paid) AS total_paid
           FROM stripe_invoices
           WHERE created_at BETWEEN ? AND ?
             AND amount_paid > 0
           GROUP BY customer_name
           ORDER BY total_paid DESC
           LIMIT 5""",
        (start_date, end_date),
    ).fetchall()

    conn.close()
    return {
        "inflows": mercury["inflows"] or 0,
        "outflows": mercury["outflows"] or 0,
        "late_invoices_count": late_count["cnt"],
        "top_customers": [dict(r) for r in top_customers],
    }


def get_ytd_owner_distributions():
    """Return total distributed to owners in 2026."""
    conn = get_connection()
    row = conn.execute(
        f"""SELECT COALESCE(SUM(ABS(amount)), 0) AS total
           FROM mercury_transactions
           WHERE amount < 0
             AND COALESCE(posted_date, created_at) >= '2026-01-01'
             AND status NOT IN ('cancelled', 'failed')
             AND {OWNER_DISTRIBUTIONS}""",
    ).fetchone()
    conn.close()
    return row["total"] or 0


def get_ytd_outflows():
    """Return total money out in 2026 via Mercury outflows."""
    conn = get_connection()
    row = conn.execute(
        f"""SELECT COALESCE(SUM(ABS(amount)), 0) AS total
           FROM mercury_transactions
           WHERE amount < 0
             AND COALESCE(posted_date, created_at) >= '2026-01-01'
             AND status NOT IN ('cancelled', 'failed')
             AND kind NOT IN ('creditCardTransaction', 'cardInternationalTransactionFee')
             {EXCLUDE_INTERNAL}""",
    ).fetchone()
    conn.close()
    return row["total"] or 0


def get_ytd_collected():
    """Return total collected in 2026 via Mercury inflows (includes Stripe payouts)."""
    conn = get_connection()
    row = conn.execute(
        f"""SELECT COALESCE(SUM(amount), 0) AS total
           FROM mercury_transactions
           WHERE amount > 0
             AND COALESCE(posted_date, created_at) >= '2026-01-01'
             AND status NOT IN ('cancelled', 'failed')
             AND kind NOT IN ('creditCardTransaction', 'cardInternationalTransactionFee')
             {EXCLUDE_INTERNAL}""",
    ).fetchone()
    conn.close()
    return row["total"] or 0


def get_last_month_collected():
    """Return total collected last month across Mercury inflows and Stripe payments."""
    now = datetime.now(timezone.utc)
    # First day of current month
    first_of_this_month = now.replace(day=1).strftime("%Y-%m-%d")
    # First day of last month
    if now.month == 1:
        first_of_last_month = now.replace(year=now.year - 1, month=12, day=1).strftime("%Y-%m-%d")
    else:
        first_of_last_month = now.replace(month=now.month - 1, day=1).strftime("%Y-%m-%d")

    conn = get_connection()
    mercury_row = conn.execute(
        f"""SELECT COALESCE(SUM(amount), 0) AS total
           FROM mercury_transactions
           WHERE amount > 0
             AND COALESCE(posted_date, created_at) >= ?
             AND COALESCE(posted_date, created_at) < ?
             AND status NOT IN ('cancelled', 'failed')
             AND kind NOT IN ('creditCardTransaction', 'cardInternationalTransactionFee')
             {EXCLUDE_INTERNAL}""",
        (first_of_last_month, first_of_this_month),
    ).fetchone()
    conn.close()
    return mercury_row["total"] or 0


def get_mtd_report(start_date: str, end_date: str):
    """Get a comprehensive month-to-date financial report."""
    conn = get_connection()

    # Mercury inflows / outflows
    mercury = conn.execute(
        f"""SELECT
               SUM(CASE WHEN amount > 0 {EXCLUDE_INTERNAL} THEN amount ELSE 0 END) AS inflows,
               SUM(CASE WHEN amount < 0 {EXCLUDE_INTERNAL} THEN ABS(amount) ELSE 0 END) AS outflows
           FROM mercury_transactions
           WHERE COALESCE(posted_date, created_at) BETWEEN ? AND ?
             AND status NOT IN ('cancelled', 'failed')
             AND kind NOT IN ('creditCardTransaction', 'cardInternationalTransactionFee')""",
        (start_date, end_date),
    ).fetchone()

    # Invoices sent this period
    invoices_sent = conn.execute(
        """SELECT COUNT(*) AS cnt, SUM(amount_due) AS total
           FROM stripe_invoices
           WHERE created_at BETWEEN ? AND ?
             AND amount_due > 0""",
        (start_date, end_date),
    ).fetchone()

    # Invoices paid this period
    invoices_paid = conn.execute(
        """SELECT COUNT(*) AS cnt, SUM(amount_paid) AS total
           FROM stripe_invoices
           WHERE paid_at BETWEEN ? AND ?
             AND amount_paid > 0""",
        (start_date, end_date),
    ).fetchone()

    # Overdue invoices (as of end_date)
    overdue = conn.execute(
        """SELECT COUNT(*) AS cnt, SUM(amount_due) AS total
           FROM stripe_invoices
           WHERE status = 'open'
             AND due_date < ?
             AND amount_due > 0""",
        (end_date,),
    ).fetchone()

    # Largest single payment received this period
    largest_payment = conn.execute(
        """SELECT customer_name, amount_paid, paid_at, number
           FROM stripe_invoices
           WHERE paid_at BETWEEN ? AND ?
             AND amount_paid > 0
           ORDER BY amount_paid DESC
           LIMIT 1""",
        (start_date, end_date),
    ).fetchone()

    # Top customers by revenue this period
    top_customers = conn.execute(
        """SELECT customer_name, SUM(amount_paid) AS total_paid
           FROM stripe_invoices
           WHERE paid_at BETWEEN ? AND ?
             AND amount_paid > 0
           GROUP BY customer_name
           ORDER BY total_paid DESC
           LIMIT 5""",
        (start_date, end_date),
    ).fetchall()

    # Top spending categories this period
    spend_rows = conn.execute(
        f"""SELECT counterparty_name, kind, SUM(ABS(amount)) AS total
           FROM mercury_transactions
           WHERE amount < 0
             AND COALESCE(posted_date, created_at) BETWEEN ? AND ?
             AND status NOT IN ('cancelled', 'failed')
             AND kind NOT IN ('creditCardTransaction', 'cardInternationalTransactionFee')
             {EXCLUDE_INTERNAL}
           GROUP BY counterparty_name, kind
           ORDER BY total DESC""",
        (start_date, end_date),
    ).fetchall()

    # Previous month for comparison
    from dateutil.relativedelta import relativedelta
    start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    prev_start = (start_dt - relativedelta(months=1)).strftime("%Y-%m-%d")
    prev_end = (start_dt - relativedelta(days=1)).strftime("%Y-%m-%d")

    prev_mercury = conn.execute(
        f"""SELECT
               SUM(CASE WHEN amount > 0 {EXCLUDE_INTERNAL} THEN amount ELSE 0 END) AS inflows,
               SUM(CASE WHEN amount < 0 {EXCLUDE_INTERNAL} THEN ABS(amount) ELSE 0 END) AS outflows
           FROM mercury_transactions
           WHERE COALESCE(posted_date, created_at) BETWEEN ? AND ?
             AND status NOT IN ('cancelled', 'failed')
             AND kind NOT IN ('creditCardTransaction', 'cardInternationalTransactionFee')""",
        (prev_start, prev_end),
    ).fetchone()

    conn.close()

    inflows = mercury["inflows"] or 0
    outflows = mercury["outflows"] or 0

    # Aggregate spend by category
    category_totals = {}
    for r in spend_rows:
        cat = categorize_vendor(r["counterparty_name"], r["kind"])
        category_totals[cat] = category_totals.get(cat, 0) + r["total"]
    top_categories = sorted(category_totals.items(), key=lambda x: -x[1])[:5]

    return {
        "inflows": inflows,
        "outflows": outflows,
        "net": inflows - outflows,
        "invoices_sent_count": invoices_sent["cnt"] or 0,
        "invoices_sent_total": invoices_sent["total"] or 0,
        "invoices_paid_count": invoices_paid["cnt"] or 0,
        "invoices_paid_total": invoices_paid["total"] or 0,
        "overdue_count": overdue["cnt"] or 0,
        "overdue_total": overdue["total"] or 0,
        "largest_payment": dict(largest_payment) if largest_payment and largest_payment["amount_paid"] else None,
        "top_customers": [dict(r) for r in top_customers],
        "top_categories": top_categories,
        "prev_inflows": prev_mercury["inflows"] or 0,
        "prev_outflows": prev_mercury["outflows"] or 0,
    }
