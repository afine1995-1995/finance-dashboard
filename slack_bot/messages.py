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


def overdue_invoice_report(invoices: list) -> list:
    """Build Block Kit blocks for an overdue invoice report with a Send All button."""
    total_overdue = sum(inv.get("amount_due", 0) for inv in invoices)

    # Group by customer
    by_customer = {}
    for inv in invoices:
        name = inv.get("customer_name", "Unknown")
        if name not in by_customer:
            by_customer[name] = {"amount": 0, "count": 0}
        by_customer[name]["amount"] += inv.get("amount_due", 0)
        by_customer[name]["count"] += 1

    client_lines = ""
    for name, info in sorted(by_customer.items(), key=lambda x: -x[1]["amount"]):
        inv_label = "invoice" if info["count"] == 1 else "invoices"
        client_lines += f"• *{name}*: ${info['amount']:,.2f} ({info['count']} {inv_label})\n"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":rotating_light: Overdue Invoice Report",
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Total Overdue:*\n${total_overdue:,.2f}"},
                {"type": "mrkdwn", "text": f"*Clients:*\n{len(by_customer)}"},
            ],
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Breakdown by Client:*\n{client_lines}",
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Send reminder to all overdue"},
                    "style": "danger",
                    "action_id": "send_all_overdue_reminders",
                    "confirm": {
                        "title": {"type": "plain_text", "text": "Send reminders?"},
                        "text": {
                            "type": "mrkdwn",
                            "text": f"This will send individual reminder emails to all {len(by_customer)} overdue clients.",
                        },
                        "confirm": {"type": "plain_text", "text": "Send All"},
                        "deny": {"type": "plain_text", "text": "Cancel"},
                    },
                },
            ],
        },
    ]
    return blocks


def mtd_report(report: dict, month_label: str, start_date: str, end_date: str) -> list:
    """Build Block Kit blocks for a month-to-date financial report."""
    inflows = report.get("inflows", 0)
    outflows = report.get("outflows", 0)
    net = report.get("net", 0)
    net_emoji = ":chart_with_upwards_trend:" if net >= 0 else ":chart_with_downwards_trend:"

    # Month-over-month comparison
    prev_inflows = report.get("prev_inflows", 0)
    prev_outflows = report.get("prev_outflows", 0)
    def _pct_change(current, previous):
        if previous == 0:
            return ""
        change = ((current - previous) / previous) * 100
        arrow = ":arrow_up:" if change >= 0 else ":arrow_down:"
        return f"  {arrow} {abs(change):.0f}% vs last month"

    inflow_change = _pct_change(inflows, prev_inflows)
    outflow_change = _pct_change(outflows, prev_outflows)

    # Top customers
    top_customers_text = ""
    for c in report.get("top_customers", []):
        top_customers_text += f"• {c['customer_name']}: ${c['total_paid']:,.2f}\n"
    if not top_customers_text:
        top_customers_text = "_No paid invoices this period_"

    # Top spend categories
    categories_text = ""
    for cat, amount in report.get("top_categories", []):
        categories_text += f"• {cat}: ${amount:,.2f}\n"
    if not categories_text:
        categories_text = "_No spending data this period_"

    # Largest payment
    largest = report.get("largest_payment")
    largest_text = "_None this period_"
    if largest:
        largest_text = f"*{largest['customer_name']}* — ${largest['amount_paid']:,.2f} (Invoice {largest.get('number', 'N/A')})"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f":ledger: {month_label} Financial Report ({start_date} to {end_date})",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*:receipt: Invoicing*",
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Invoices Sent:*\n{report['invoices_sent_count']} (${report['invoices_sent_total']:,.2f})"},
                {"type": "mrkdwn", "text": f"*Invoices Paid:*\n{report['invoices_paid_count']} (${report['invoices_paid_total']:,.2f})"},
                {"type": "mrkdwn", "text": f"*Overdue:*\n:warning: {report['overdue_count']} invoices (${report['overdue_total']:,.2f})"},
                {"type": "mrkdwn", "text": f"*Largest Payment:*\n{largest_text}"},
            ],
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*:bank: Cash Flow*",
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Total Revenue (Inflows):*\n${inflows:,.2f}{inflow_change}"},
                {"type": "mrkdwn", "text": f"*Total Outflows:*\n${outflows:,.2f}{outflow_change}"},
                {"type": "mrkdwn", "text": f"*Net:* {net_emoji}\n${net:,.2f}"},
            ],
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*:trophy: Top Customers by Revenue*\n{top_customers_text}",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*:money_with_wings: Top Spending Categories*\n{categories_text}",
            },
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
