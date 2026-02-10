import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from config import Config

logger = logging.getLogger(__name__)

_template_dir = Path(__file__).resolve().parent.parent / "templates"
_jinja_env = Environment(loader=FileSystemLoader(str(_template_dir)))


def send_reminder_email(to_email: str, invoice_data: dict):
    """Send a payment reminder email via Gmail SMTP.

    invoice_data should contain: customer_name, number, amount_due,
    currency, due_date, hosted_invoice_url
    """
    html_template = _jinja_env.get_template("email_reminder.html")
    text_template = _jinja_env.get_template("email_reminder.txt")

    html_body = html_template.render(**invoice_data)
    text_body = text_template.render(**invoice_data)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Payment Reminder — Invoice {invoice_data.get('number', '')}"
    msg["From"] = Config.GMAIL_ADDRESS
    msg["To"] = to_email
    msg["Cc"] = Config.EMAIL_CC

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    recipients = [to_email]
    if Config.EMAIL_CC:
        recipients.append(Config.EMAIL_CC)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(Config.GMAIL_ADDRESS, Config.GMAIL_APP_PASSWORD)
            server.sendmail(Config.GMAIL_ADDRESS, recipients, msg.as_string())
        logger.info(f"Reminder email sent to {to_email} (CC: {Config.EMAIL_CC})")
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        raise
