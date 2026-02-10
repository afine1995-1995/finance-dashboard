import logging
from datetime import datetime, timedelta, timezone

from services.stripe_service import sync_invoices, sync_subscriptions
from services.mercury_service import sync_transactions
from services.slack_service import post_message
from models.queries import get_late_invoices, mark_notified, get_period_summary
from slack_bot.messages import late_payment_alert, weekly_summary

logger = logging.getLogger(__name__)


def sync_all_data():
    """Sync Mercury transactions and Stripe invoices."""
    logger.info("Running scheduled data sync...")
    try:
        mc = sync_transactions()
        logger.info(f"Mercury: {mc} transactions synced")
    except Exception as e:
        logger.error(f"Mercury sync error: {e}")

    try:
        sc = sync_invoices()
        logger.info(f"Stripe: {sc} invoices synced")
    except Exception as e:
        logger.error(f"Stripe sync error: {e}")

    try:
        ss = sync_subscriptions()
        logger.info(f"Stripe: {ss} active subscriptions synced")
    except Exception as e:
        logger.error(f"Stripe subscription sync error: {e}")


def check_late_payments():
    """Check for late Stripe invoices and send Slack alerts."""
    logger.info("Checking for late payments...")
    late = get_late_invoices()

    if not late:
        logger.info("No new late payments found")
        return

    logger.info(f"Found {len(late)} new late invoice(s)")
    for invoice in late:
        blocks = late_payment_alert(invoice)
        text = f"Late payment: {invoice.get('customer_name', 'Unknown')} — ${invoice.get('amount_due', 0):,.2f}"
        try:
            post_message(blocks=blocks, text=text)
            mark_notified(invoice["id"])
        except Exception as e:
            logger.error(f"Failed to send Slack alert for {invoice['id']}: {e}")


def post_weekly_summary():
    """Post a weekly financial summary to Slack."""
    logger.info("Posting weekly summary...")
    now = datetime.now(timezone.utc)
    end_date = now.strftime("%Y-%m-%d")
    start_date = (now - timedelta(days=7)).strftime("%Y-%m-%d")

    summary = get_period_summary(start_date, end_date)
    blocks = weekly_summary(summary, start_date, end_date)
    text = f"Weekly summary: ${summary['inflows']:,.2f} in / ${summary['outflows']:,.2f} out"

    try:
        post_message(blocks=blocks, text=text)
    except Exception as e:
        logger.error(f"Failed to post weekly summary: {e}")
