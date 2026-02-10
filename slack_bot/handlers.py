import logging

from services.stripe_service import get_fresh_invoice
from services.email_service import send_reminder_email
from services.slack_service import post_message
from models.queries import get_all_late_invoices, mark_email_sent

logger = logging.getLogger(__name__)


def register_handlers(app):
    """Register Slack Bolt action handlers."""

    @app.action("send_reminder_email")
    def handle_send_reminder(ack, body, say):
        ack()

        invoice_id = body["actions"][0]["value"]
        user = body["user"]["username"]
        channel = body["channel"]["id"]
        message_ts = body["message"]["ts"]

        logger.info(f"User @{user} clicked Send Reminder Email for invoice {invoice_id}")

        # Fetch fresh data from Stripe
        invoice = get_fresh_invoice(invoice_id)
        if not invoice:
            post_message(
                blocks=[{
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f":x: Could not fetch invoice `{invoice_id}` from Stripe."},
                }],
                text=f"Could not fetch invoice {invoice_id}",
                channel=channel,
                thread_ts=message_ts,
            )
            return

        customer_email = invoice.get("customer_email")
        if not customer_email:
            post_message(
                blocks=[{
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f":x: No email address on file for this customer."},
                }],
                text="No customer email on file",
                channel=channel,
                thread_ts=message_ts,
            )
            return

        try:
            send_reminder_email(customer_email, invoice)
            mark_email_sent(invoice_id)
            post_message(
                blocks=[{
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f":white_check_mark: Reminder email sent to *{customer_email}* "
                            f"for invoice *{invoice.get('number', invoice_id)}*"
                        ),
                    },
                }],
                text=f"Reminder sent to {customer_email}",
                channel=channel,
                thread_ts=message_ts,
            )
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            post_message(
                blocks=[{
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f":x: Failed to send email: {e}"},
                }],
                text=f"Email send failed: {e}",
                channel=channel,
                thread_ts=message_ts,
            )

    @app.action("send_all_overdue_reminders")
    def handle_send_all_overdue(ack, body, say):
        ack()

        user = body["user"]["username"]
        channel = body["channel"]["id"]
        message_ts = body["message"]["ts"]

        logger.info(f"User @{user} clicked Send reminder to all overdue")

        invoices = get_all_late_invoices()
        if not invoices:
            post_message(
                blocks=[{
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": ":white_check_mark: No overdue invoices found — nothing to send."},
                }],
                text="No overdue invoices",
                channel=channel,
                thread_ts=message_ts,
            )
            return

        sent = 0
        failed = 0
        skipped = 0
        results = []

        for inv in invoices:
            invoice_id = inv["id"]
            # Fetch fresh data from Stripe
            invoice = get_fresh_invoice(invoice_id)
            if not invoice:
                skipped += 1
                results.append(f":warning: `{inv.get('number', invoice_id)}` — could not fetch from Stripe")
                continue

            customer_email = invoice.get("customer_email")
            if not customer_email:
                skipped += 1
                results.append(f":warning: `{invoice.get('number', invoice_id)}` ({invoice.get('customer_name', 'Unknown')}) — no email on file")
                continue

            try:
                send_reminder_email(customer_email, invoice)
                mark_email_sent(invoice_id)
                sent += 1
                results.append(f":white_check_mark: `{invoice.get('number', invoice_id)}` — sent to {customer_email}")
            except Exception as e:
                failed += 1
                results.append(f":x: `{invoice.get('number', invoice_id)}` — failed: {e}")
                logger.error(f"Email send failed for {invoice_id}: {e}")

        summary = f"*Sent:* {sent}  |  *Failed:* {failed}  |  *Skipped:* {skipped}"
        detail = "\n".join(results)

        post_message(
            blocks=[
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f":email: *Bulk Reminder Results*\n{summary}"},
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": detail},
                },
            ],
            text=f"Bulk reminders: {sent} sent, {failed} failed, {skipped} skipped",
            channel=channel,
            thread_ts=message_ts,
        )
