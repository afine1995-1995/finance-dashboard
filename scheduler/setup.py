import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config import Config
from scheduler.jobs import sync_all_data, check_late_payments, post_weekly_summary, post_mtd_report, post_overdue_report

logger = logging.getLogger(__name__)


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()

    # Data sync — daily at 6 AM
    scheduler.add_job(
        sync_all_data,
        trigger=CronTrigger(hour=6, minute=0),
        id="sync_all_data",
        name="Sync Mercury + Stripe data",
        replace_existing=True,
    )

    # Late payment check — daily at configured hour
    scheduler.add_job(
        check_late_payments,
        trigger=CronTrigger(hour=Config.LATE_CHECK_HOUR, minute=0),
        id="check_late_payments",
        name="Check for late Stripe payments",
        replace_existing=True,
    )

    # Weekly summary — configured day and hour
    scheduler.add_job(
        post_weekly_summary,
        trigger=CronTrigger(
            day_of_week=Config.WEEKLY_SUMMARY_DAY,
            hour=Config.WEEKLY_SUMMARY_HOUR,
            minute=0,
        ),
        id="post_weekly_summary",
        name="Post weekly Slack summary",
        replace_existing=True,
    )

    # Month-to-date financial report — Friday at 9 AM Eastern
    scheduler.add_job(
        post_mtd_report,
        trigger=CronTrigger(
            day_of_week="fri",
            hour=9,
            minute=0,
            timezone="US/Eastern",
        ),
        id="post_mtd_report",
        name="Post month-to-date financial report to Slack",
        replace_existing=True,
    )

    # Overdue invoice report — Monday and Thursday at 9 AM Eastern
    scheduler.add_job(
        post_overdue_report,
        trigger=CronTrigger(
            day_of_week="mon,thu",
            hour=9,
            minute=0,
            timezone="US/Eastern",
        ),
        id="post_overdue_report",
        name="Post overdue invoice report to Slack",
        replace_existing=True,
    )

    return scheduler
