import os
import sqlite3

from config import Config


def get_connection():
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path) as f:
        schema = f.read()
    conn = get_connection()
    conn.executescript(schema)
    # Add paid_at column if missing (migration for existing DBs)
    try:
        conn.execute("ALTER TABLE stripe_invoices ADD COLUMN paid_at TEXT")
    except sqlite3.OperationalError:
        pass  # column already exists
    conn.close()
