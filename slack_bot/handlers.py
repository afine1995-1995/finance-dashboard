import logging

from services.stripe_service import get_fresh_invoice
from services.email_service import send_reminder_email
from services.slack_service import post_message
from models.queries import mark_email_sent

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
