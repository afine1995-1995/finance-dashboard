import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Stripe
    STRIPE_API_KEY = os.getenv("STRIPE_API_KEY", "")

    # Mercury
    MERCURY_API_TOKEN = os.getenv("MERCURY_API_TOKEN", "")

    # Slack
    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
    SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN", "")
    SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID", "")

    # Gmail
    GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
    GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
    EMAIL_CC = os.getenv("EMAIL_CC", "ali@understoryagency.com")

    # Flask
    FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))

    # Scheduler
    SYNC_INTERVAL_HOURS = int(os.getenv("SYNC_INTERVAL_HOURS", "4"))
    LATE_CHECK_HOUR = int(os.getenv("LATE_CHECK_HOUR", "9"))
    WEEKLY_SUMMARY_DAY = os.getenv("WEEKLY_SUMMARY_DAY", "mon")
    WEEKLY_SUMMARY_HOUR = int(os.getenv("WEEKLY_SUMMARY_HOUR", "9"))

    # Dashboard auth (optional — skip auth when unset for local dev)
    DASHBOARD_USER = os.getenv("DASHBOARD_USER", "")
    DASHBOARD_PASS = os.getenv("DASHBOARD_PASS", "")

    # Database
    DB_PATH = os.getenv("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "finance.db"))
