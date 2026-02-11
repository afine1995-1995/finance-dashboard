import logging
from datetime import datetime, timezone

import stripe

from config import Config
from models.queries import upsert_stripe_invoice, upsert_stripe_subscription, log_sync

logger = logging.getLogger(__name__)

stripe.api_key = Config.STRIPE_API_KEY


def _ts_to_datestr(ts):
    """Convert a Unix timestamp to YYYY-MM-DD string, or None."""
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def _ts_to_iso(ts):
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def sync_invoices():
    """Fetch all Stripe invoices and cache them in SQLite."""
    logger.info("Syncing Stripe invoices...")
    count = 0
    try:
        for invoice in stripe.Invoice.list(limit=100).auto_paging_iter():
            customer_name = None
            customer_email = None
            if invoice.customer_name:
                customer_name = invoice.customer_name
            if invoice.customer_email:
                customer_email = invoice.customer_email

            # Extract paid_at from status_transitions if available
            paid_at = None
            if hasattr(invoice, "status_transitions") and invoice.status_transitions:
                paid_ts = getattr(invoice.status_transitions, "paid_at", None)
                if paid_ts:
                    paid_at = _ts_to_iso(paid_ts)

            upsert_stripe_invoice({
                "id": invoice.id,
                "number": invoice.number,
                "customer_id": invoice.customer if isinstance(invoice.customer, str) else None,
                "customer_name": customer_name,
                "customer_email": customer_email,
                "amount_due": invoice.amount_due / 100.0,
                "amount_paid": invoice.amount_paid / 100.0,
                "currency": invoice.currency,
                "status": invoice.status,
                "due_date": _ts_to_datestr(invoice.due_date),
                "created_at": _ts_to_iso(invoice.created),
                "paid_at": paid_at,
                "hosted_invoice_url": invoice.hosted_invoice_url,
            })
            count += 1

        log_sync("stripe", count)
        logger.info(f"Synced {count} Stripe invoices")
    except Exception as e:
        logger.error(f"Stripe sync failed: {e}")
        log_sync("stripe", count, status="error", error_message=str(e))
        raise

    return count


def sync_subscriptions():
    """Fetch all active Stripe subscriptions and cache them in SQLite."""
    logger.info("Syncing Stripe subscriptions...")
    count = 0
    try:
        # Expand customer so we get the name without extra API calls
        for sub in stripe.Subscription.list(
            status="active", limit=100, expand=["data.customer"]
        ).auto_paging_iter():
            # Calculate monthly amount from subscription items
            monthly_amount = 0
            for item in sub.items.data:
                price = item.price
                amount = (price.unit_amount or 0) / 100.0
                quantity = item.quantity or 1
                interval = "month"
                interval_count = 1
                if price.recurring:
                    interval = price.recurring.interval or "month"
                    interval_count = price.recurring.interval_count or 1
                if interval == "year":
                    monthly_amount += (amount * quantity) / (12 * interval_count)
                elif interval == "month":
                    monthly_amount += (amount * quantity) / interval_count
                elif interval == "week":
                    monthly_amount += (amount * quantity * 52) / (12 * interval_count)
                else:
                    monthly_amount += amount * quantity

            # Get customer name from expanded customer object
            customer_name = "Unknown"
            customer_id = None
            if isinstance(sub.customer, str):
                customer_id = sub.customer
            else:
                customer_id = sub.customer.id
                customer_name = sub.customer.name or sub.customer.email or "Unknown"

            upsert_stripe_subscription({
                "id": sub.id,
                "customer_id": customer_id,
                "customer_name": customer_name,
                "status": sub.status,
                "monthly_amount": round(monthly_amount, 2),
                "currency": sub.currency,
                "current_period_start": _ts_to_datestr(sub.current_period_start),
                "current_period_end": _ts_to_datestr(sub.current_period_end),
            })
            count += 1

        log_sync("stripe_subscriptions", count)
        logger.info(f"Synced {count} active Stripe subscriptions")
    except Exception as e:
        logger.error(f"Stripe subscription sync failed: {e}")
        log_sync("stripe_subscriptions", count, status="error", error_message=str(e))
        raise

    return count


def get_balance() -> dict:
    """Fetch the current Stripe balance."""
    try:
        balance = stripe.Balance.retrieve()
        # available and pending are lists of {amount, currency} objects
        available = sum(b.amount for b in balance.available) / 100.0
        pending = sum(b.amount for b in balance.pending) / 100.0
        return {"available": available, "pending": pending, "total": available + pending}
    except Exception as e:
        logger.error(f"Failed to fetch Stripe balance: {e}")
        return {"available": 0, "pending": 0, "total": 0}


def get_fresh_invoice(invoice_id: str) -> dict | None:
    """Fetch a single invoice directly from Stripe API (for email sending)."""
    try:
        inv = stripe.Invoice.retrieve(invoice_id)
        return {
            "id": inv.id,
            "number": inv.number,
            "customer_name": inv.customer_name,
            "customer_email": inv.customer_email,
            "amount_due": inv.amount_due / 100.0,
            "currency": inv.currency,
            "status": inv.status,
            "due_date": _ts_to_datestr(inv.due_date),
            "hosted_invoice_url": inv.hosted_invoice_url,
        }
    except Exception as e:
        logger.error(f"Failed to fetch invoice {invoice_id}: {e}")
        return None
