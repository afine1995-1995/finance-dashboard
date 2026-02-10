from datetime import datetime, timezone


def late_payment_alert(invoice: dict) -> list:
    """Build Block Kit blocks for a late payment notification with a Send Email button."""
    due = invoice.get("due_date", "unknown")
    days_overdue = ""
    if due and due != "unknown":
        try:
            due_dt = datetime.strptime(due, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - due_dt
            days_overdue = f"  ({delta.days} days overdue)"
        except ValueError:
            pass

    amount = invoice.get("amount_due", 0)
    currency = (invoice.get("currency") or "usd").upper()

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":warning: Late Payment Detected",
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Customer:*\n{invoice.get('customer_name', 'Unknown')}"},
                {"type": "mrkdwn", "text": f"*Invoice:*\n{invoice.get('number', invoice.get('id', 'N/A'))}"},
                {"type": "mrkdwn", "text": f"*Amount Due:*\n${amount:,.2f} {currency}"},
                {"type": "mrkdwn", "text": f"*Due Date:*\n{due}{days_overdue}"},
            ],
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Send Reminder Email"},
                    "style": "primary",
                    "action_id": "send_reminder_email",
                    "value": invoice.get("id", ""),
                },
            ],
        },
    ]
    return blocks


def weekly_summary(summary: dict, start_date: str, end_date: str) -> list:
    """Build Block Kit blocks for a weekly financial summary."""
    inflows = summary.get("inflows", 0)
    outflows = summary.get("outflows", 0)
    net = inflows - outflows
    net_emoji = ":chart_with_upwards_trend:" if net >= 0 else ":chart_with_downwards_trend:"

    top_customers_text = ""
    for c in summary.get("top_customers", []):
        top_customers_text += f"• {c['customer_name']}: ${c['total_paid']:,.2f}\n"
    if not top_customers_text:
        top_customers_text = "_No paid invoices this period_"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f":bar_chart: Weekly Financial Summary ({start_date} to {end_date})",
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Total Inflows:*\n${inflows:,.2f}"},
                {"type": "mrkdwn", "text": f"*Total Outflows:*\n${outflows:,.2f}"},
                {"type": "mrkdwn", "text": f"*Net:* {net_emoji}\n${net:,.2f}"},
                {"type": "mrkdwn", "text": f"*Late Invoices:*\n{summary.get('late_invoices_count', 0)}"},
            ],
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Top Customers by Revenue:*\n{top_customers_text}",
            },
        },
    ]
    return blocks
