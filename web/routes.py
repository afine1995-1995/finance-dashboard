import logging
from datetime import datetime, timezone

from flask import Blueprint, Response, jsonify, render_template, request

from models.queries import get_open_invoices_for_client, mark_email_sent
from services.email_service import send_reminder_email
from services.stripe_service import get_fresh_invoice
from scheduler.jobs import post_weekly_summary, post_overdue_report
from web.charts import (
    build_in_vs_out_chart,
    build_profit_margin_chart,
    build_days_to_pay_chart,
    build_revenue_by_client_chart,
    build_concentration_risk_chart,
    build_expected_revenue_chart,
    build_spend_by_category_chart,
    build_spend_detail_chart,
)

logger = logging.getLogger(__name__)

bp = Blueprint("web", __name__, template_folder="templates", static_folder="static", static_url_path="/assets")


@bp.route("/")
def dashboard():
    return render_template("dashboard.html")


@bp.route("/api/charts/in-vs-out")
def chart_in_vs_out():
    return Response(build_in_vs_out_chart(), mimetype="application/json")


@bp.route("/api/charts/profit-margin")
def chart_profit_margin():
    return Response(build_profit_margin_chart(), mimetype="application/json")


@bp.route("/api/charts/days-to-pay")
def chart_days_to_pay():
    return Response(build_days_to_pay_chart(), mimetype="application/json")


@bp.route("/api/charts/revenue-by-client")
def chart_revenue_by_client():
    return Response(build_revenue_by_client_chart(), mimetype="application/json")


@bp.route("/api/charts/concentration-risk")
def chart_concentration_risk():
    return Response(build_concentration_risk_chart(), mimetype="application/json")


@bp.route("/api/charts/expected-revenue")
def chart_expected_revenue():
    return Response(build_expected_revenue_chart(), mimetype="application/json")


@bp.route("/api/charts/spend-by-category")
def chart_spend_by_category():
    return Response(build_spend_by_category_chart(), mimetype="application/json")


@bp.route("/api/charts/spend-detail")
def chart_spend_detail():
    month = request.args.get("month", "")
    category = request.args.get("category", "")
    return Response(build_spend_detail_chart(month, category), mimetype="application/json")


@bp.route("/api/slack/weekly-summary", methods=["GET", "POST"])
def api_trigger_weekly_summary():
    try:
        post_weekly_summary()
        return jsonify({"success": True, "message": "Weekly summary posted to Slack"})
    except Exception as e:
        logger.error(f"Failed to trigger weekly summary: {e}")
        return jsonify({"error": str(e)}), 500


@bp.route("/api/slack/overdue-report", methods=["GET", "POST"])
def api_trigger_overdue_report():
    try:
        post_overdue_report()
        return jsonify({"success": True, "message": "Overdue report posted to Slack"})
    except Exception as e:
        logger.error(f"Failed to trigger overdue report: {e}")
        return jsonify({"error": str(e)}), 500


@bp.route("/api/invoices/open")
def api_open_invoices():
    client = request.args.get("client", "")
    if not client:
        return jsonify({"error": "client parameter required"}), 400

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows = get_open_invoices_for_client(client)

    invoices = []
    for r in rows:
        is_overdue = bool(r["due_date"] and r["due_date"] < today)
        invoices.append({
            "id": r["id"],
            "number": r["number"],
            "customer_email": r["customer_email"],
            "amount_due": r["amount_due"],
            "due_date": r["due_date"],
            "hosted_invoice_url": r["hosted_invoice_url"],
            "is_overdue": is_overdue,
            "email_sent": bool(r["email_sent"]),
        })

    return jsonify(invoices)


@bp.route("/api/invoices/send-reminder", methods=["POST"])
def api_send_reminder():
    data = request.get_json(silent=True) or {}
    invoice_id = data.get("invoice_id")
    if not invoice_id:
        return jsonify({"error": "invoice_id required"}), 400

    invoice = get_fresh_invoice(invoice_id)
    if not invoice:
        return jsonify({"error": f"Could not fetch invoice {invoice_id} from Stripe"}), 404

    customer_email = invoice.get("customer_email")
    if not customer_email:
        return jsonify({"error": "No email address on file for this customer"}), 400

    try:
        send_reminder_email(customer_email, invoice)
        mark_email_sent(invoice_id)
        return jsonify({"success": True, "email": customer_email})
    except Exception as e:
        logger.error(f"Email send failed for {invoice_id}: {e}")
        return jsonify({"error": f"Failed to send email: {e}"}), 500
