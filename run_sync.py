"""Standalone sync script — runs Mercury + Stripe sync and exits.

Designed to be called by Windows Task Scheduler every 30 minutes so
charts stay fresh even when the Flask app is not running.

Usage (run from the finance-dashboard directory):
    python run_sync.py
"""
import sys
import os
import logging

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from scheduler.jobs import sync_all_data

if __name__ == "__main__":
    sync_all_data()
